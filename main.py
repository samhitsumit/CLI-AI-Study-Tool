from funcs import GenMultiQ, useMultiQ, genOE, useOE, GenFlashcards, GenFlashcardsFromImage, useFlashcards, clear, getJson, writeJson
from funcs import ask_ai, checkMis, displaySaved, aPFeedback, summary_from_image, genMultiQN, genSimMCQ, genFB, useFB, genSimOE
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
import questionary as quest
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.styles import Style
from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.shortcuts import radiolist_dialog
from rich.panel import Panel
import os, time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

number_validator = Validator.from_callable(
    lambda text: text.isdigit(),
    error_message="Please enter a number",
    move_cursor_to_end=True,
)

console = Console()

def ct():
    input("Press enter when you are done...")

fileses = []
for root, dirs, files in os.walk("/Users/samhits"):
    for file in files:
        fileses.append(file)

while True:
    action = radiolist_dialog(
    title="Choose an option",
    text="Select one:",
    values=[
        ("Z", "Summarize notes"),
        ('Q', 'Questions'),
        ("V", "View statistics"),
        ("T", "Talk to AI"),
        ('S', "View saved questions"),
        ("A", "Ask about saved questions you got wrong"),
        ("E", 'Enter image of question you got wrong for feedback'),
        ("X", 'Exam mode'),
        ('G', 'Generate questions similar to others')
    ],
).run()
    
    if action == 'Q':
        val = radiolist_dialog(
            title='Choose an option',
            text='Select one',
            values=[
                ("F", "Flashcards"),
                ("M", "Multi-choice questions"),
                ("O", "OE questions")#,
                # ('B', 'Fill in the blanks')
            ]
        ).run()
        if val == "F":
            variant = radiolist_dialog(
                title="Choose an option",
                text="Select one:",
                values=[
                    ("I", "Generate from image of notes"),
                    ("N", "Generate from text of notes")
                ]
            ).run()

            if variant == "I":
                notes = prompt("Enter the note's filename:")
                num = int(prompt("How many flashcards would you like:"))
                fls = GenFlashcardsFromImage(notes, num)
                print(fls)
                input("Press enter when you are ready...")
                clear()
                useFlashcards(fls)
                ct()

            if variant == "N":
                notes = prompt("Enter your notes here :", multiline=True)
                num = int(prompt("How many flashcards would you like:"))
                fls = GenFlashcards(notes, num)
                print(fls)
                input("Press enter when you are ready...")
                clear()
                useFlashcards(fls)
                ct()


        if val == "M":
            variant = radiolist_dialog(
                title="Choose an option",
                text="Select one:",
                values=[
                    ("T", "Generate from topics"),
                    ("N", "Generate from notes"),
                    ("I", "Generate questions from image notes")
                ]
            ).run()

            if variant == "T":
                topics = prompt("What topics would you like:")
                num = prompt("Type how many questions you want:")
                grade = prompt("What grade are you in:")
                queses = GenMultiQ(topics, grade, num=num)
                useMultiQ(queses)
            elif variant == "N":
                notes = prompt("Enter your notes :", multiline=True)
                num = prompt("How many questions would you like :")
                queses = genMultiQN(notes, num)
                useMultiQ(queses)
            else:
                image = prompt("Enter the image filename :")
                notes = aPFeedback(image)
                num = prompt("How many questions would you like :")
                queses = genMultiQN(notes, num)
                useMultiQ(queses)

        if val == "O":
            topics = prompt("What topics would you like:")
            num = prompt("Type how many questions you want:")
            grade = prompt("What grade are you in:")
            queses = genOE(topics, grade, num=num)
            useOE(queses)  
            ct()

        if val == 'B':
            topics = prompt('What topics would you like :')
            grade = prompt('What grade are you in :')
            num = prompt('How many questions would you like :')
            queses = genFB(grade, num, topics)
            useFB(queses)    
            ct()

    if action == "V":
        data = getJson()
        today = datetime.now().date()
        dates = []

        for i in range(7):
            d = today - timedelta(days=i)
            dates.append(d.strftime("%d/%m/%Y"))
        okDates = []
        values = []

        oneWeekAgo = datetime.now() - timedelta(days=7)
        for dateString in dates:
            date = datetime.strptime(dateString, "%d/%m/%Y")
            if date > oneWeekAgo:
                okDates.append(dateString)

        for i in okDates:
            try:    
                values.append(data['History'][i])       
            except KeyError:
                values.append(0)     
        values.reverse()

        plt.plot(okDates, values)
        plt.tight_layout()
        plt.show()        

        display = f"""
Correct answers : {data["QCount"]["Correct"]}
Wrong answers : {data["QCount"]["Wrong"]}
Total questions answered : {data["QCount"]["Correct"] + data["QCount"]["Wrong"]}
"""
        print(display)
        input("Press return when you are done reading...")

    if action == "T":
        while True:    
            userA = prompt(placeholder='You may type in anything. Type "exit" to end the conversation.')
            if userA == 'exit':
                break
            else:
                console.print(Markdown(ask_ai(userA)))

    if action == 'A':
        checkMis()
        ct()

    if action == 'S':
        displaySaved()
        ct()

    if action == 'E':
        filename = input("Enter the image's filename :")
        grade = input("What grade are you in: :")
        stuff = aPFeedback(filename, grade)
        console.print(Markdown(stuff))
        with open(stuff[:50] + ".md", "w") as file:
            file.write(stuff)
        print("The notes have been saved to" + f"{stuff[:50]}.md")    
        ct()

    if action == "Z":
        filename = input("Enter your's notes' filename :")
        console.print(Markdown(summary_from_image(filename)), markup=True)
        ct()

    if action == 'X':
        mcqCount = int(prompt("How many MCQs would you like :", validator=number_validator))
        oeqCount = int(prompt("How many OEQs would you like :", validator=number_validator))

        topics = prompt('Choose the topics for your exam:')
        grade = prompt('What grade are you in:')

        mcqQueses = GenMultiQ(topics, grade, mcqCount)
        oeqQueses = genOE(topics, grade, oeqCount)

        useMultiQ(mcqQueses)
        useOE(oeqQueses)

    if action == 'G':
        variant = radiolist_dialog(
            title="Choose an option",
            text="Select one:",
            values=[
                ('O', 'OEQs'),
                ('M', 'MCQs')
            ]
        ).run()   
        if variant == 'M':
            image = prompt("Enter the filename of the question :", 
                           completer=WordCompleter(fileses, ignore_case=True),
                            complete_while_typing=True)
            num = prompt("How many questions would you like :")
            queses = genSimMCQ(image, num=num)
            useMultiQ(queses)

        if variant == "O":
            image = prompt("Enter the filename of the question :", 
                           completer=WordCompleter(fileses, ignore_case=True),
                            complete_while_typing=True)
            num = prompt("How many questions would you like :")
            queses = genSimOE(image, num)
            useOE(queses)