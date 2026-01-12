# The app you want to build
You want to develop an application that reads Cobol source code from Cobol files and builds a Python representation of the data structures defined in the Cobol source code.
The Cobol data structures are defined in the `DATA DIVISION.` of the Cobol source code.
The Python representation of these data structures must be able to hold the same values that are held by the Cobol data structures when a `MOVE` instruction is executed.
Consider the following example:
- The Cobol code has this instruction `MOVE QU01-DATA  TO  LAST-DATA`
- `LAST-DATA` is a data structure defined as:
```
01 LAST-DATA.
    03 NAME PIC X(10).
    03 TYPE.
        05 CODE PIC 9(5) COMP-3.
        05 DESC PIC X(10).
```
- You have saved in a log the value a string containing the values held in the variable `QU01-DATA` when the `MOVE` instruction is executed
- You want to build a Python representation of `LAST-DATA` that describes the structure of `LAST-DATA` and has a method or a function that can fill a Python object with the values held in the string of the log
- At the end the Python object should be able to return the value of any of the field defined in `LAST-DATA`

The application must be able to manage common patterns such as:
- use of `FILLER` to group related data definitions
- use of `OCCURS` for repetitions
- use of `REDEFINE`

At the moment you want to consider only the most common data types and you are not interested to cater for all edge cases.
If your logic encounters an edge case, it just writes a warning message on a warning file and sets as "unknown" (or something similar) the Python object representing the Cobol data structure you have not been able to manage.

# Your task
Your task is:
- to understand the requirements of the app you want to build,
- determine which is the best approach. Some potential approaches are
    1) build a Parser with a standard approch (a syntax, a Lexer and so on)
    2) build some custom code that is able to interpret Cobol source code without the potential complexity of a standard parser
- write a summary document in markdown with the results of your analysis and your recommendations

Simplicity is a great value for this app.
In the tradeoff between simplicity and completeness, prefer simplicity as long as the design is able to manage the most commmon cases of data definitions in Cobol programs.


# Review
Use three deep dive agents to review the recommendations. Ensure that there are no bugs or massive gaps in the solution proposed. 