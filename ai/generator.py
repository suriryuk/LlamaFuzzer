import asyncio
import urllib

from fastapi import WebSocket

from unsloth import FastLanguageModel

from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate

from utils import attack_map
from ai.template import template_format

hacker_template = '''You are an expert hacker and exploit developer. Generate only the attack payload for this vulnerability. No additional text or descriptions - just tell us what we need to enter.
{context}

Question: {question}
'''

template = '''Below is an instruction that describes a task. Write a response that appropriately completes the request.
{context}

Question: {question}
'''
prompt = ChatPromptTemplate.from_template(template)
hacker_prompt = ChatPromptTemplate.from_template(hacker_template)

def is_valid_utf8(string: str) -> bool:
    try:
        string.encode('utf-8').decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False
    except UnicodeEncodeError:
        return False
    
def URL_encode(query: str):
    return urllib.parse.quote(query, safe="'\" ")

async def process_chat(question: str, context: str) -> str:
    llm = ChatOllama(model='llama3-ko', temperature=0.9)

    input_data = {
        'context' : context,
        'question' : question
    }

    chain = prompt | llm | StrOutputParser()
    # output = chain.invoke(input_data)
    output = await asyncio.to_thread(lambda: chain.invoke(input_data))
    print(output)

    return output

async def process_fuzz_payload(attack: str):
    print(f'{attack_map[attack]}_model')
    llm = ChatOllama(model=f'{attack_map[attack]}_model', temperature=0.9)

    input_data = {
        'context' : '',
        'question' : f"Create a new {attack} payload."
    }

    chain = hacker_prompt | llm | StrOutputParser()

    # 생성된 payload를 저장할 리스트
    results = []
    i = 1
    payload_cnt = 50
    while i != (payload_cnt + 1):
        result = await asyncio.to_thread(lambda: chain.invoke(input_data))
        result = result.strip()

        # utf-8 인코딩 문자열인지 확인
        if not is_valid_utf8(result):
            continue
        
        # Web Request에 넣기 위해 URL 인코딩
        encoded_result = URL_encode(result)
        results.append(encoded_result)

        print(i, result)

        i += 1

    # 템플릿에 넣기 위해 join
    if attack == 'SQL Injection':
        queries = "\n".join(f"        - \"{URL_encode(query).replace('"', '\\"')}\"" for query in results)
    elif attack == 'XSS':
        queries = "\n".join(f"        - \"{query.replace('\\', '\\\\').replace('"', '\\"')}\"" for query in results)
    elif attack == 'RCE':
        queries = "\n".join(f"        - \"{query.replace('\\', '\\\\').replace('"', '\\"')}\"" for query in results)
    elif attack == 'File Inclusion':
        queries = "\n".join(f"        - \"{query.replace('\\', '\\\\').replace('"', '\\"')}\"" for query in results)

    # 생성된 payload를 nuclei 템플릿에 포맷팅
    nuclei_template = template_format(attack, queries)

    # 템플릿을 파일로 저장
    file_path = "./ai/payloads.yaml"
    with open(file_path, 'w') as f:
        f.write(nuclei_template)