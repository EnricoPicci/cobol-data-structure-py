You are a Python programmer with 20 years of experience.
You also know Cobol programming language.

You have developed this Python application that anonymize Cobol code.

Cobol code lines (in fixed mode) can have "sequence numbers" or "identification tags" in the first 6 positions of each line. 
In the anonymized version of the source files we need to clean these first 6 positions if "sequence numbers" or "identification tags" are found.

Your task is:
- implement cleanup of the first 6 positions
- add tests to test this new requirement
- ensure that all test pass at the end of the implementation
- update the documentation documents where needed

# 1 Refinement
By default the sequence area should be cleaned. Update the implementation accordingly.

# 2 Fix bug
Clean the sequence area also for comment lines