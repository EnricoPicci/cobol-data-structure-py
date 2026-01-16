You are a Python programmer with 20 years of experience.
You also know Cobol programming language.

You have developed this Python application that anonymize Cobol code.
Currently the application keeps the comments untouched.

However, the requirement is the following:
- the text of each comment should be transformed in a sort of "blah blah" - in other words you need to keep the comment but the comment does not have to have any correlation with the original text of the comment
- the number of lines should remain the same, no comment must be removed

Your task is:
- to understand how this application works
- implement the change described above
- change the existing tests so that they still work
- add any other necessary test

# 1 Fix bug
Your changes do not implement the new requirement.
For example, consider the file "EDMCA020.cpy" in the folder "original-cobol-source".
If you anonymize it you generate a new file which has exactly the same comments as the original one has.
For instance, the start of the anonymized file is still like this:
      * 
      * @(#)EDMCA020.cpy:DGN_OSPCBL:0A27961.A-SRC;6
      * 
      ******************************************************************
      *                                                                *
      *    SISTEMA PORTAFOGLIO RAMI DANNI                              *
      *    AGGIORNAMENTO PARTE AMMINISTRATIVA                          *
      *                                                                *
      *----------------------------------------------------------------*
      *                                                                *
      *    IDENTIFICATIVO CONTRATTO: "A_020"                           *
      *                                                                *
      ******************************************************************

      while is should be
      * 
      * @(#)EDMCA020.cpy:DGN_OSPCBL:0A27961.A-SRC;6
      * 
      ******************************************************************
      *                                                                *
      *    SISTEMA PORTAFOGLIO RAMI DANNI                              *
      *    AGGIORNAMENTO PARTE AMMINISTRATIVA                          *
      *                                                                *
      *----------------------------------------------------------------*
      *                                                                *
      *    IDENTIFICATIVO CONTRATTO: "A_020"                           *
      *                                                                *
      ******************************************************************

Your task is:
- fix the implementation so that it complies with the new requirement
- adjust tests as required
- add any needed test which is currently missing
