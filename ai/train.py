# This project uses the unsloth library (https://github.com/unsloth/unsloth),
# licensed under the Apache 2.0 License

from unsloth import FastLanguageModel, is_bfloat16_supported
from datasets import Dataset
from trl import SFTTrainer
from transformers import TrainingArguments

import torch

import pandas as pd
import wandb
import json
import io
import sys
import tqdm

def capture_output(func):
    captured_output = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured_output

    func()

    sys.stdout = original_stdout
    return captured_output.getvalue()


def logger(msg: str, mode='INFO'):
    if mode == 'INFO':
        print('\033[92m' + f'| INFO | trainer.UnslothTrainer | {msg}' + '\033[0m')
    elif mode == 'ERROR':
        print('\033[91m' + f'| ERROR | trainer.UnslothTrainer | {msg}' + '\033[0m')

class UnslothTrainer:
    def __init__(self, attack: str, attack_map: dict):
        self.attack = attack
        self.attack_map = attack_map

        self.max_seq_length = 4096
        self.dtype = None
        self.load_in_4bit = True

        # AlpacaPrompt를 사용하여 지시사항 포맷팅
        self.alpaca_prompt = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

        ### Instruction:
        {}

        ### Response:
        {}"""

        if attack not in attack_map.keys():
            logger('No data exists for that attack!', mode='ERROR')
            exit()

        logger('UnslothTrainer Ready', mode='INFO')

    def load_model(self):
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name = "unsloth/llama-3-8b-bnb-4bit",
            max_seq_length=self.max_seq_length,
            dtype=self.dtype,
            load_in_4bit=self.load_in_4bit,
        )

        # 모델 초기화
        self.model = FastLanguageModel.get_peft_model(
            self.model,
            r=16, # 8, 16, 32, 64, 128 권장
            lora_alpha=16,
            lora_dropout=0, # dropout 지원
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=3407,
            use_rslora=False, # 순위 안정화 LoRA 지원 여부
            loftq_config=None, # LoftQ 지원
        )

        self.EOS_TOKEN = self.tokenizer.eos_token

        logger('Load Model Success', mode='INFO')

        return self.model, self.tokenizer

    def load_dataset(self, filename):
        try:
            # load dataset
            # df = pd.read_csv(f"./ai/csv/{self.attack_map[self.attack]}_payload.csv", encoding='latin1')
            df = pd.read_csv(f"./csv/{filename}", encoding='latin1')

            # Dataframe to JSON
            json_df = df.to_dict(orient='records')

            # Alpaca Prompt Formatting
            formatted_data = []
            for entry in json_df:
                instruction = f'Create a new {self.attack} payload.'
                output = entry['payload']
                text = self.alpaca_prompt.format(instruction, output) + self.EOS_TOKEN
                formatted_data.append({'text': text})
            
            # list to Dataset object
            dataset = Dataset.from_list(formatted_data)

            logger(f'Dataset json dump success', mode='INFO')

            return dataset
        except Exception as e:
            logger(f'Dataset json dump error : {e}', mode='ERROR')

    async def train(self, websocket, dataset):
        try:
            gpu_stats = torch.cuda.get_device_properties(0)
            start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
            max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
            logger(f'GPU = {gpu_stats.name}. Max memory = {max_memory} GB')
            logger(f'{start_gpu_memory} GB of memory reserved.')
            await websocket.send_text(f'GPU = {gpu_stats.name}. Max memory = {max_memory} GB')
            await websocket.send_text(f'{start_gpu_memory} GB of memory reserved.')

            logger(capture_output(self.model.print_trainable_parameters).strip())
            await websocket.send_text(capture_output(self.model.print_trainable_parameters).strip())

            self.tokenizer.padding_side = "right" # tokenizer의 패딩을 오른쪽으로 설정

            # wandb 초기화
            wandb.init(project="unsloth_AI_Fuzzer", entity="dnjsgh1209", name=f"{self.attack}")

            self.trainer = SFTTrainer(
                model=self.model,
                tokenizer=self.tokenizer,
                train_dataset=dataset,
                # eval_dataset=dataset,
                max_seq_length=self.max_seq_length,
                dataset_num_proc=2,
                packing=False,
                dataset_text_field="text",
                args=TrainingArguments(
                    per_device_train_batch_size=2, # 각 디바이스당 훈련 배치 크기
                    gradient_accumulation_steps=8, # 그래디언트 누적 단계
                    warmup_steps=5, # warmup 스텝 수
                    num_train_epochs=3,
                    max_steps=80,
                    logging_steps=1, # logging 스텝 수
                    learning_rate=2e-4,
                    fp16=not is_bfloat16_supported(),
                    bf16=is_bfloat16_supported(),
                    # fp16=not torch.cuda.is_bf16_supported(),
                    # bf16=torch.cuda.is_bf16_supported(),
                    optim="adamw_8bit",
                    weight_decay=0.01,
                    lr_scheduler_type="linear",
                    seed=3407,
                    output_dir=f"./results/{self.attack_map[self.attack]}_results",
                    report_to="wandb"
                ),
            )

            logger('Model Fine-Tuning Start', mode='INFO')
            await websocket.send_text('Model Fine-Tuning Start')
            self.trainer_stats = self.trainer.train()
            logger('Model Fine-Tuning End', mode='INFO')
            await websocket.send_text('Model Fine-Tuning End')

            logger('Model Save Start', mode='INFO')
            await websocket.send_text('Model Save Start')
            # model save
            base = f"./models/{self.attack_map[self.attack]}_model"

            self.model.save_pretrained_gguf(
                base,
                self.tokenizer,
                quantization_method='q8_0'
            )

            self.model.save_pretrained_merged(
                base,
                self.tokenizer,
                save_method="merged_16bit"
            )
            logger('Model save End', mode='INFO')
            await websocket.send_text('Model save End')

            # Modelfile Generate
            logger('Modelfile Generate Start', mode='INFO')
            await websocket.send_text('Modelfile Generate Start')

            modelfile = open('./Modelfile', 'r').read() # Modelfile Sample Read

            with open(f'{base}/Modelfile', 'w') as f: # Modelfile Sample Copy
                f.write(modelfile)

            logger('Modelfile Generate End', mode='INFO')
            await websocket.send_text('Modelfile Generate End')

            # print(self.tokenizer._ollama_modelfile)
            # with open(f'{base}/Modelfile', 'w') as f:
            #     f.write(self.tokenizer._ollama_modelfile)
        except Exception as e:
            logger(f'Model Fine-Tuning Error : {e}', mode='ERROR')
            await websocket.send_text(f'Model Fine-Tuning Error : {e}')