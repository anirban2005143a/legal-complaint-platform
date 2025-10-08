import os, requests, json, time, re, csv
from dotenv import load_dotenv
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
# import google.generativeai as genai
# from transformers import AutoModelForCausalLM, AutoTokenizer
# from peft import PeftModel

# Env variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_STUDIO_API_KEY = os.getenv("GOOGLE_STUDIO_API_KEY")
GEMINI_API_KEY=os.getenv("GEMINI_PRO_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}
HF_API_URL = os.getenv("HF_API_URL")
HF_API_KEY = os.getenv("HF_API_KEY")


ipc_to_bns = {}
section_info = {}

def home(request):
    return render(request, 'user/home.html')

def query_huggingface(prompt, retries=3, timeout=200):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HF_API_KEY}"
    }

    data = {
        "inputs": prompt
    }

    for attempt in range(retries):
        try:
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json=data,
                timeout=timeout
            )

            if response.status_code != 200:
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                return f"Hugging Face API error: {response.status_code} - {response.text}"

            result = response.json()
            # print(result)  # debug

            # If HuggingFace text generation model, usually output is in result[0]['generated_text']
            if isinstance(result, list) and "generated_text" in result[0]:
                raw_output = result[0]["generated_text"]
                return raw_output
            else:
                return result

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(5)
            else:
                return f"Hugging Face API request failed after {retries} attempts: {str(e)}"

def query_groq(prompt, retries=3, timeout=30):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-8b-instant", # <- changed this
        "messages": [{"role": "user", "content": prompt}]
    }

    for attempt in range(retries):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=timeout
            )

            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"Groq API error: {response.text}"

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(5) 
            else:
                return f"Groq API request failed after {retries} attempts: {str(e)}"
            
def query_gemini(prompt, retries=3, timeout=30):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }

    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=timeout)

            if response.status_code == 200:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return f"Gemini API error: {response.text}"

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(5)
            else:
                return f"Gemini API request failed after {retries} attempts: {str(e)}"

# def query_LSI_Gemma_model(prompt):

def normalize_response(resp):
    if isinstance(resp, (list, dict)):
        return resp

    if isinstance(resp, str):
        cleaned = resp.strip()

        if cleaned.startswith("[") and not cleaned.endswith("]"):
            cleaned += "]"

        cleaned = re.sub(r",\s*([\]\}])", r"\1", cleaned)

        try:
            return json.loads(cleaned)
        except:
            items = re.findall(r'"(.*?)"', cleaned)
            if items:
                return items

    return resp

def load_ipc_to_bns_mapping_csv(csv_file="ipc_to_bns.csv"):
    global ipc_to_bns
    BASE_DIR = os.path.dirname(__file__)
    csv_path = os.path.join(BASE_DIR,"mappings",csv_file)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ipc = row["ipc_section"].strip()
            bns = row["bns_section"].strip()
            ipc_to_bns[ipc] = bns if bns else ""

def load_ipc_to_bns_mapping_jsonl(jsonl_file="ipc_to_bns.jsonl"):
    global ipc_to_bns
    BASE_DIR = os.path.dirname(__file__)
    jsonl_path = os.path.join(BASE_DIR, "mappings", jsonl_file)

    mappings = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)

            ipc = row.get("IPC Sections", "").strip()
            bns = row.get("BNS Sections/Subsections", "").strip()

            if not bns:
                continue
            
            ipc = re.sub(r"\s+\(", "(", ipc)
            bns = re.sub(r"\s+\(", "(", bns)

            ipc_to_bns[ipc] = bns
            # print(f"ipc:{ipc} <=> bns:{bns}")
            mappings = mappings +1
                
def convert_ipc_to_bns(response_item):
    m = re.search(r"Section\s+(\d+[A-Z]?)\s+of\s+The Indian Penal Code", response_item, re.I)
    if m:
        ipc_section = m.group(1)
        bns_section = ipc_to_bns.get(ipc_section, "")
        if bns_section:
            return f"Section {bns_section} of The Bharatiya Nyaya Sanhita, 2023"
        else:
            return f"Section {ipc_section} of The Indian Penal Code, 1860"
    return response_item

def load_section_url_info(json_file="url_info.json"):
    global section_info
    BASE_DIR = os.path.dirname(__file__)
    json_path = os.path.join(BASE_DIR, "mappings", json_file)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        section_info = {key: value for key, value in data.items()}

        # print("\nLoaded Section Info:")
        # for i, (key, value) in enumerate(section_info.items(), start=1):
        #     print(f"{i}. {key} -> {value}")

    except FileNotFoundError:
        print("File not found at:", json_path)
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        



@csrf_exempt
def upload_complaint(request):
    if request.method == 'POST':
        BASE_DIR = os.path.dirname(__file__)

        file_path = os.path.join(BASE_DIR, "json_inputs", "short_queries.json")
        output_path = os.path.join(BASE_DIR, "results","gemini_short_query_results.json")

        # Load the mappings
        load_ipc_to_bns_mapping_jsonl("ipc_to_bns.jsonl")

        # Load the input queries
        with open(file_path, "r", encoding="utf-8") as f:
            complaints_data = json.load(f) 

        query_texts = [obj.get("query-text", "") for obj in complaints_data]
        end_index = len(query_texts)-1

        results = []

        structured_prompt_template = """
                    READ ALL LINES CAREFULLY BEFORE PRODUCING THE OUTPUT.
                    ** refers to important details

                    You are an information extraction engine for Indian law.
                    You must ONLY output the JSON array described below. 
                    **No other additional response than what is asked, No explanations, No context, no markdown, no text, no notes before or after the brackets.**

                    Given the following query text, identify all relevant and necessary Indian legal sections and Acts, giving their full names.

                    Query:
                    {{user_query}}

                    STRICT OUTPUT RULES (violating any rule makes the output wrong):

                    1. You MUST output ONLY a valid JSON array of strings.
                    2. First line must be exactly: "["
                    3. Last line must be exactly: "]"
                    4. Each item must be: **"Section <section number> of The <full act name>, <year>"**
                        - Always include the word "The" at the start of the act name.
                        - Always give the full name of the act.
                        - Always include the year of the act.
                        - Expand abbreviations (e.g., IPC → The Indian Penal Code, 1860).
                    5. Each item must be on its own line, enclosed in double quotes.
                    6. Place a comma after each item EXCEPT the last one.
                    7. No spaces before or after square brackets beyond what is shown.
                    8. No extra characters, no extra lines, no explanations, no markdown, no commentary, no notes before or after the array.
                    9. Always check for and include Indian Penal Code (IPC) sections where relevant.
                    10. If no sections are found with certainty, output exactly:
                    [
                    ]
                    (two lines only, nothing else).
                    """



        first = True
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("[")
            f.flush()
            os.fsync(f.fileno())

        try:
            start_index = 0
            for i, q in enumerate(query_texts[start_index:end_index+1], start=start_index):
                while True:
                    prompt = structured_prompt_template.replace("{{user_query}}", q)
                    raw_response = query_groq(prompt)

                    # if "groq api error" in raw_response.lower():
                    #     print(f"Groq API error on query {i+1}, retrying in 5 seconds...")
                    #     time.sleep(5)
                    #     continue

                    # raw_response = query_gemini(prompt)
                    
                    try:
                        parsed_response = json.loads(raw_response)
                    except json.JSONDecodeError:
                        parsed_response = normalize_response(raw_response)
                    
                    if not isinstance(parsed_response, list):
                        parsed_response = [convert_ipc_to_bns(item) for item in parsed_response]
                    
                    bns_converted = [convert_ipc_to_bns(item) for item in parsed_response]

                    record = {
                        "query_number": i+1,
                        "llm_response": parsed_response,
                        "bns_converted_response": bns_converted
                    }

                    with open(output_path, "a", encoding="utf-8") as f:
                        if first:
                            f.write("\n" + json.dumps(record, ensure_ascii=False, indent=4))
                            first = False
                        else:
                            f.write(",\n" + json.dumps(record, ensure_ascii=False, indent=4))
                        f.flush()
                        os.fsync(f.fileno())

                    print(f"query {i+1}: {parsed_response}")
                    time.sleep(3)
                    break
        finally:
            with open(output_path, "a", encoding="utf-8") as f:
                f.write("\n]\n")
                f.flush()
                os.fsync(f.fileno())
        
        return JsonResponse({"status": "done", "results": results})

    return JsonResponse({"error": "Invalid method"}, status=405)




@csrf_exempt
def process_complaint(request):
    if request.method == 'POST':
        try:
            language = request.POST.get('language', '').strip()
            
            if not language:
                return JsonResponse({"error": "No language selected"}, status=400)
            
            user_query = ""
            
            if 'text' in request.POST:
                user_query = request.POST.get('text', '').strip()
            
            elif 'pdf' in request.FILES:
                pdf_file = request.FILES['pdf']
                user_query = f"PDF file uploaded: {pdf_file.name}"
            
            elif 'doc' in request.FILES:
                doc_file = request.FILES['doc']
                user_query = f"DOC file uploaded: {doc_file.name}"
            
            if not user_query:
                return JsonResponse({"error": "No query provided"}, status=400)

            load_ipc_to_bns_mapping_jsonl("ipc_to_bns.jsonl")
            load_section_url_info("url_info.json")

            structured_prompt_template = """
            You are a legal expert on Indian law. Given the text below, identify all applicable legal sections and their full act names. Follow these rules exactly:
            1. Identify every relevant provision (section number + full act name) you are 100% certain applies under Indian statutes.
            2. Output only one list in square brackets, formatted like: ["Section X of Act Name"; "Section Y of Act Name"; …]
            - Each entry must be a quoted string with the section first, then the full act name.
            - Each entry needs both section number AND full act name
            - Separate entries with a semicolon.
            - Do not include anything outside this single list.
            3. Exclude any entry missing either section or act (no incomplete pairs).
            4. Do not repeat identical section-act pairs (no duplicates).
            5. Do not add explanations, labels, or extra text—only the list itself.
            6. Always spell out the full name of each act (no abbreviations).
            7. Include only provisions that are clearly and directly relevant (no speculative or uncertain entries).
            
            Query:
            {{user_query}}
            """.strip()
            # structured_prompt_template = """
            # READ ALL LINES CAREFULLY BEFORE PRODUCING THE OUTPUT.
            # ** refers to important details

            # You are an information extraction engine for Indian law.
            # You must ONLY output the JSON array described below. 
            # **No other additional response than what is asked, No explanations, No context, no markdown, no text, no notes before or after the brackets.**

            # Given the following query text, identify all relevant and necessary Indian legal sections and Acts, giving their full names.

            # Query:
            # {{user_query}}

            # STRICT OUTPUT RULES (violating any rule makes the output wrong):

            # 1. You MUST output ONLY a valid JSON array of strings.
            # 2. First line must be exactly: "["
            # 3. Last line must be exactly: "]"
            # 4. Each item must be: **"Section <section number> of The <full act name>, <year>"**
            #     - Always include the word "The" at the start of the act name.
            #     - Always give the full name of the act.
            #     - Always include the year of the act.
            #     - Expand abbreviations (e.g., IPC → The Indian Penal Code, 1860).
            # 5. Each item must be on its own line, enclosed in double quotes.
            # 6. Place a comma after each item EXCEPT the last one.
            # 7. No spaces before or after square brackets beyond what is shown.
            # 8. No extra characters, no extra lines, no explanations, no markdown, no commentary, no notes before or after the array.
            # 9. Always check for and include Indian Penal Code (IPC) sections where relevant.
            # 10. If no sections are found with certainty, output exactly:
            # [
            # ]
            # (two lines only, nothing else).
            # """

            prompt = structured_prompt_template.replace("{{user_query}}", user_query)

            # raw_response = query_huggingface(prompt).strip()
            # raw_response = query_gemini(prompt).strip()
            # raw_response = query_LSI_Gemma_model(prompt).strip()
            
            # response = query_LSI_Gemma_model("Explain binary search in simple terms")
            # print(response)

            # raw_response = query_groq(prompt)

            # if "api error" in raw_response.lower():
            #     return JsonResponse(
            #         {"status": "error", "message": "Server error. Please try again later."},
            #         status=500
            #     )

            # raw_response = re.sub(r"^```(?:json)?", "", raw_response.strip())
            # raw_response = re.sub(r"```$", "", raw_response.strip())

            # try:
            #     parsed_response = json.loads(raw_response)
            # except json.JSONDecodeError:
            #     parsed_response = [
            #         line.strip().strip('"')
            #         for line in raw_response.splitlines()
            #         if line.strip() and not line.strip().startswith("[") and not line.strip().startswith("]")
            #     ]

            # if not isinstance(parsed_response, list):
            #     parsed_response = [str(parsed_response)]

            # cleaned_response = []
            # for item in parsed_response:
            #     if isinstance(item, str):
            #         item = re.sub(r'(\b\d{4})[,"\']*\s*$', r'\1', item)
            #     cleaned_response.append(item)
            #     # print(item)

            # bns_converted = parsed_response

            """this is my code Anirban Das from IIT ISM"""
            # Extract the output string from the dictionary
            raw_response = query_huggingface(prompt)['output']
            # print(raw_response)

            # If somehow raw_response is not a string, convert it
            if not isinstance(raw_response, str):
                raw_response = str(raw_response)

            # Remove leading/trailing spaces
            raw_response = raw_response.strip()

            # Replace semicolons with commas to make it valid JSON
            raw_response = raw_response.replace(';', ',')

            # Remove Markdown ```json ``` wrapper if present
            raw_response = re.sub(r"^```(?:json)?", "", raw_response)
            raw_response = re.sub(r"```$", "", raw_response)

            # Try parsing JSON
            try:
                parsed_response = json.loads(raw_response)
            except json.JSONDecodeError:
                # Fallback: split by lines and strip quotes
                parsed_response = [
                    line.strip().strip('"').strip("'")
                    for line in raw_response.splitlines()
                    if line.strip() and not line.strip().startswith("[") and not line.strip().startswith("]")
                ]

            # Ensure it's always a list
            if not isinstance(parsed_response, list):
                parsed_response = [str(parsed_response)]

            # Clean each item (remove trailing quotes/commas)
            cleaned_response = []
            for item in parsed_response:
                if isinstance(item, str):
                    item = re.sub(r'(\b\d{4})[,"\']*\s*$', r'\1', item)
                    item = item.strip()
                cleaned_response.append(item)

            bns_converted = cleaned_response  # use cleaned_response here

            sections_urls = []

            for sec in bns_converted:
                # print("raw:", repr(sec))  # debug to see hidden chars

                sec_clean = sec.strip().lower() if isinstance(sec, str) else str(sec).lower()
                matched = None
                for k, v in section_info.items():
                    if k.strip().lower() == sec_clean:
                        matched = v
                        break

                if matched:
                    sections_urls.append(f"https://indiankanoon.org/doc/{matched}/")
                else:
                    sections_urls.append("https://indiankanoon.org/")  # dummy link

            return JsonResponse({
                "status": "done",
                "language": language,
                "query": user_query,
                "llm_response": parsed_response,
                "bns_converted_response": bns_converted,
                "section_info": sections_urls
            }, json_dumps_params={'ensure_ascii': False, 'indent': 4})


        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=405)