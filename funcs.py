import ollama
import easyocr
import random
import os
import re
from pathlib import Path
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from rich.markdown import Markdown
from rich.console import Console
from prompt_toolkit import prompt as porm
import time, json
from datetime import datetime
import base64, matplotlib

console = Console()

def image_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

class FlexibleCompleter(Completer):
    def __init__(self, words):
        self.words = words

    def get_completions(self, document, complete_event):
        text = document.text.lower()

        for word in self.words:
            if text in word.lower():
                yield Completion(
                    word,
                    start_position=-len(document.text)
                )

def getJson(filename="data.json"):
    with open(filename, "r") as f:
        return json.load(f)
    
def writeJson(data, filename="data.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)    

MODEL = "gemma4:latest"
# =========================
# AI HELPER
# =========================

chat_history = [
    {
        "role": "system",
        "content": "You are a helpful AI tutor."
    }
]

def ask_ai(user_prompt):
    global chat_history

    # Add the user's message
    chat_history.append({
        "role": "user",
        "content": user_prompt
    })

    # Send the whole conversation
    response = ollama.chat(
        model=MODEL,
        messages=chat_history
    )

    # Save the AI's reply
    assistant_reply = response["message"]["content"]

    chat_history.append({
        "role": "assistant",
        "content": assistant_reply
    })

    return assistant_reply


# =========================
# OCR
# =========================

reader = easyocr.Reader(['en'])

def OCR(filename):

    result = reader.readtext(
        filename,
        paragraph=True
    )

    text = ""

    for item in result:
        text += item[1] + "\n"

    return text


def reOCR(text):

    prompt = f"""
The following text came from OCR.

Fix:
- spelling mistakes
- formatting
- line breaks

OCR TEXT:{text}
"""

    return ask_ai(prompt)


# =========================
# UTILITIES
# =========================

def clear():
    os.system("cls" if os.name == "nt" else "clear")


# =========================
# SUMMARY
# =========================

def summary_from_text(text):

    prompt = f"""
Summarise these notes.

Rules:
- Maximum 10 bullet points
- Very concise
- Keep only important information

Notes : {text}
"""

    return ask_ai(prompt)


def summary_from_image(filename):

    prompt = f"""
Could you summarise the notes in the image i will provide you.
Only give 10 bullet points. You may use markdown syntax. You can not use latex syntax. Each bullet point can only have a maximum of 15 words.
"""
    response : str = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images" : [image_to_b64(filename)]
            }    
        ]
    )["message"]["content"]
    return response

# =========================
# FLASHCARDS
# =========================

def GenFlashcards(notes,cardnum):

    prompt = f"""
You are creating study flashcards for student.

STRICT RULES:

- Use ONLY information found in the notes.
- Make sure the answers to the flashcards are as detailed as the content in the image of the notes.
- Do NOT use outside knowledge.
- Do NOT add extra facts.
- Do NOT infer information.
- If information is missing, skip that flashcard.
- Do not use markdown.
- Do not use LaTeX.
- Keep answers short.

Generate exactly {cardnum} flashcards if possible.

Format:

Q: Question
A: Answer

NOTES:

{notes}
"""

    return ask_ai(prompt)


def GenFlashcardsFromImage(filename, cardnum):
    prompt = f"""
I will give you an image of notes taken down by a student. I need you to extract the text
in the image and type that out. Do not respond with anything else.
"""
    response : str = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images" : [image_to_b64(filename)]
            }    
        ]
    )["message"]["content"]

    return GenFlashcards(response, cardnum)

def useFlashcards(flashcards):

    questions = []
    answers = []

    for line in flashcards.splitlines():

        if line.startswith("Q:"):
            questions.append(line)

        elif line.startswith("A:"):
            answers.append(line)

    while questions:

        index = random.randint(0, len(questions)-1)

        print()
        print(questions[index])

        answer = input("Answer: ")

        prompt = f"""
Question:
{questions[index]}

Expected:
{answers[index]}

Student:
{answer}

Is the student's answer essentially correct?

Reply only YES or NO.
"""

        result = ask_ai(prompt)

        if "yes" in result.lower():

            print("Correct!")
            data = getJson()
            data["QCount"]["Correct"] += 1
            writeJson(data)

            questions.pop(index)
            answers.pop(index)

        else:

            print("Wrong!")
            data = getJson()
            data["QCount"]["Wrong"] += 1
            writeJson(data)
            print(answers[index])

        input("\nPress Enter...")


# =========================
# MULTIPLE CHOICE
# =========================

def genMultiQN(notes, num):
    p1 = f"""
Create {num} MCQ questions. Make sure you do not include markdown syntax. Do not use latex syntax.
Make sure only one of the options are correct. Do not create your own information.

Notes:
{notes}

Format:

Q. Question

1. Option
2. Option
3. Option
4. Option

ANSWER: 2
"""
    return ask_ai(p1)

def GenMultiQ(topics, grade, num):

    topic_text = "\n".join(topics)

    prompt = f"""
Create {num} MCQ questions. Make sure you do not include markdown syntax. Do not use latex syntax.
Make sure only one of the options are correct.

Topics:
{topic_text}

Grade:
{grade}

Format:

Q. Question

1. Option
2. Option
3. Option
4. Option

ANSWER: 2
"""

    return ask_ai(prompt)


def useMultiQ(questions):

    blocks = re.split(r'(?=Q\.\s)', questions)

    score = 0
    total = 0

    for block in blocks:

        block = block.strip()

        if not block:
            continue

        lines = block.splitlines()

        question = ""
        options = []
        answer = ""

        for line in lines:

            line = line.strip()

            if line.startswith("Q. "):
                question = line[3:]

            elif line.startswith(("1.", "2.", "3.", "4.")):
                options.append(line)

            elif line.startswith("ANSWER:"):
                answer = line.replace("ANSWER:", "").strip()

        if len(options) != 4:
            continue

        total += 1

        clear()

        print(question)
        print()

        for option in options:
            print(option)

        saveON = input("Would you like to save this questions (y/n):")

        user = input("\nAnswer (1-4): ")
        if saveON == "y":
            data = getJson()
            data["SQuestions"].append({"Q" : question, "O" : options, "A" : answer, "UA" : user} )
            writeJson(data)

        if user == answer:

            print("\nCorrect!")
            data = getJson()
            data["QCount"]["Correct"] += 1
            writeJson(data)
            score += 1

        else:

            print("\nWrong!")
            data = getJson()
            data["QCount"]["Wrong"] += 1
            print(f"Correct answer: {options[int(answer)-1]}")

        today = datetime.now().strftime("%d/%m/%Y")
        count = None
        try:
            count = data["History"][today]
        except KeyError:
            count = 0    

        data['History'][today] = count + 1
        writeJson(data)

        input("\nPress Enter...")

    print(f"\nFinal Score: {score}/{total}")
    time.sleep(1)


# =========================
# OPEN ENDED
# =========================

def genOE(topic, grade, num):

    prompt = f"""
Create {num} questions. Each question must have the question text and they must be answered using sentence based answers.
.Make sure you do not include markdown syntax or latex syntax.

Topic:
{topic}

Grade:
{grade}

For EACH question also generate a model answer.

Format:

Q. Question

ANSWER:
*Model answer*
"""

    return ask_ai(prompt)
def useOE(questions : str):
    qHeaders = []
    answers = []
    for index, line in enumerate(questions.splitlines()):
        if line.startswith("Q."):
            qHeaders.append(line)

        if line.startswith("ANSWER"):
            answers.append(questions.splitlines()[index + 1])

    for index, i in enumerate(qHeaders):
        print(i)
        ans = input("What is the answer:")

        prompt = f"""
You are a strict examiner marking a student's answer.

Question:
{i}

Correct Answer:
{answers[index]}

Student Answer:
{ans}

Rules:
- "I don't know", "maybe", "not sure" = ALWAYS WRONG
- Be strict, do not be generous
- The answer is correct ONLY if it clearly matches the correct answer
- Ignore politeness or partial effort

Task:
1. Decide if the student's answer is correct or incorrect
2. If incorrect, briefly explain why and what is missing
3. If the student explicitly responds saying that they do not know the answer, give a slightly more detailed explanation.

Output format (STRICT):

Result: YES or NO
Explanation: (ONLY write this line if Result is NO or if taks 3 is true. Otherwise omit it.)

- Keep explanation under 5 sentences
- Use simple markdown if needed (bold, bullet points allowed)
"""   
        response : str = ask_ai(prompt)
        result = None
        explanation = None
        
        for line in response.splitlines():
            if line.startswith('Result:'):
                result = line.strip('Result :')

            if line.startswith("Explanation:"):
                explanation = line.strip('Explanation :')   

        if "yes" in result.lower():
            print("Correct")
            data = getJson()
            data["QCount"]["Correct"] += 1
            writeJson(data)
        else:
            print("Wrong")    
            console.print(Markdown(explanation))
            data = getJson()
            data["QCount"]["Correct"] += 1
            writeJson(data)

        today = datetime.now().strftime("%d/%m/%Y")
        count = None
        try:
            count = data["History"][today]
        except KeyError:
            count = 0    

        data['History'][today] = count + 1
        writeJson(data)    

def checkMis():
    questions = []
    data = getJson()

    for i in data["SQuestions"]:
        questions.append(i["Q"])

    completer = FlexibleCompleter(questions)

    selected = porm(
        "Search question: ",
        completer=completer
    )
    index = questions.index(selected)

    options = data["SQuestions"][index]["O"]
    answer = data["SQuestions"][index]["A"]
    userAnswer = data["SQuestions"][index]["UA"]

    if userAnswer != answer:
        promptA = f"""
    Your job is to explain why a student got this question wrong {selected}.
    The options were {options}. The correct answer was {answer} but he or she chose {userAnswer}.
    Use markdown syntax. Do not use latex syntax. Write a maximum of 400 words
    """
        print(ask_ai(promptA))
        yOn = porm("Would you like to unsave this question. This can not be undone.(y/n):")
        if yOn == "y":
            data = getJson()
            del data["SQuestions"][index]
            writeJson(data)


def displaySaved():
    data = getJson()
    for part in data["SQuestions"]:
        question = part["Q"]
        oString = ""
        for option in part["O"]:
            oString += f"{option}\n"

        toPrint = f"""
{question}
{oString}
The answer : {part["A"]}
Your answer : {part["UA"]}
"""    
        console.print(Markdown(toPrint), markup=True)
        
def aPFeedback(image, grade):
    p1 = """
Analyse this question thta a student got wrong and convert it to a text discription including the diagramm and the question itself.
Format like this: If there are options then put them in.

Diagramm : *discription. Only put this text in one line*
Question : *the question text itself. Only put this text in one line*
Options : *options Only put the text in one line. ONLY HAVE THIS LINE IF THE QUESTIONS HAS OPTIONS.*
Answer : *The students's answer. Only put this text in one line*
"""
    response : str = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": p1,
                "images" : [image_to_b64(image)]
            }    
        ]
    )["message"]["content"]
    o = None

    for line in response.splitlines():
        if line.startswith("Diagramm :"):
            d = line.removesuffix("Diagramm :")
        elif line.startswith("Question :"):
            q = line.removesuffix("Question :")  
        elif line.startswith("Answer :"):    
            a = line.removesuffix("Answer :")
        elif line.startswith("Options : "):
            o = line.removesuffix("Options :")

    p2 = f"""
A student got this question wrong. Could you give him some feedback on how he can get the question correct the next time.
This is a description of the diagramm : {d}
This is the question : {q}
{f"The options are {o} " if o else ""}
This was his answer : {a}
"""        

    response = ask_ai(p2) 
    return response

def genSimMCQ(image, num):
    prompt = f"""
I will provide you with an image of a question that a student got wrong. Could generate {num} Multi Choice Questions similar to it.
Make sure only one of the options are correct. Do not use latex or markdown syntax.

Format:

Q. Question

1. Option
2. Option
3. Option
4. Option

ANSWER: 2
"""
    

    response : str = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images" : [image_to_b64(Path(image).resolve())]
            }    
        ]
    )["message"]["content"]

    return response

def genSimOE(image, num):
    prompt = f"""
I will provide you with an image of a question that a student got wrong. Could you generate {num} Written answer questions similar
to the question i provided. Do not use markdwon or latex syntax. Also provide a model answer to each question.
Format:

Q. Question

ANSWER:
*Model answer*
"""
    response : str = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images" : [image_to_b64(image)]
            }    
        ])
    return response["message"]["content"]

def genFB(grade, num, topics):
    prompt = f"""
Your task is to generate exactly {num} "fill in the blanks" questions for a student in grade{grade}.
The topics for the questions are {topics}. Do not use latex or markdown syntax. Give 2 words that could fit in the blank 
and make sense. You must

Format like this:
*text*_______*text*
ANSWER :*one word* *next word*
"""
    response = ask_ai(prompt)
    return response

def useFB(queses : str):
    texts = []
    answers = []
    for line in queses.splitlines():
        if '_' in line:
            texts.append(line)
        if 'ANSWER' in line:
            line = line.strip('ANSWER :')
            toFill = []
            for i in line.split(' '):
                toFill.append(i.lower())
            answers.append(toFill)   

    data = getJson()            
    for index, i in enumerate(texts):
        ans = input(f'{i}. What goes in the blank:')
        if ans.lower() in answers[index]:
            print('Correct')
            data["QCount"]['Correct'] += 1
        else:
            print('Wrong')
            data["QCount"]['Wrong'] += 1
            prompt = f"""
A student filled in the blank in {i} with {ans}.
Could you explain why he or she it wrong.You may use markdown syntax but keep the explanation under 6 senetances.
You are not allowed to use latex syntax.
"""       
            response = ask_ai(prompt)
            console.print(Markdown(response))   

        today = datetime.now().strftime("%d/%m/%Y")
        count = None
        try:
            count = data["History"][today]
        except KeyError:
            count = 0    

        data['History'][today] = count + 1
        writeJson(data)    
if __name__ == "__main__":
    print(os.path.exists("notes2.png"))
    print(OCR("notes2.png"))