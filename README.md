# LlamaFuzzer
Llama3 8B 모델을 활용한 AI Fuzzer입니다.

현재 SQL Injection, XSS, Command Injection(RCE), File Inclusion 공격을 Llama3가 Payload를 생성하여 Fuzzing에 사용 가능합니다.

공격 기법을 추가하고 싶으시면 데이터셋을 추가로 학습시켜서 추가하시면 됩니다.

FastAPI를 활용하여 웹에서 모델 학습, Fuzzing을 할 수 있도록 개발하였습니다.

## 설치
LlamaFuzzer를 설치하기 전, poetry와 nuclei를 설치해야 합니다. [poetry 설치](https://python-poetry.org/docs/) [nuclei 설치](https://github.com/projectdiscovery/nuclei)
```bash
$ git clone https://github.com/suriryuk/LlamaFuzzer.git
$ cd LlamaFuzzer
$ poetry install
```

## 사용법
FastAPI 서버를 실행시키는 방법은 간단합니다. main.py를 실행하기만 하면 됩니다.
```bash
$ python main.py
```
### Payload
Payload 페이지는 단순히 LLM 모델이 생성한 Payload만 받아보고 싶을 때 사용하는 페이지입니다.

Attack Type을 선택하고, 요청을 보내면 LLM 모델이 생성한 Payload를 Nuclei Template의 형태로 반환합니다.

![]()

### Train
Train 페이지는 LLM 모델을 학습시킬 수 있는 페이지입니다.

학습 데이터셋을 업로드하고 Train 버튼을 누르면 서버에서 학습이 진행됩니다. 학습 진행 상황은 로그를 통해 확인할 수 있습니다.

![Train image](images/train_page.png)


## Open source used
- [nuclei](https://github.com/projectdiscovery/nuclei): MIT License
- [unsloth](https://github.com/unsloth/unsloth): Apache 2.0 License