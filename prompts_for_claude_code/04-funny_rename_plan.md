You are a Python programmer with 20 years of experience.
You also know Cobol programming language.

You have developed this Python application that anonymize Cobol code.
Currently the application gives new anonymized names which are quite dull.

For example, <snippet> is a snippet of anonymized code:
<snippet>
      ******************************************************************              
       SC0000000000000000036            SECTION.                                      
      ******************************************************************              
                                                                                      
           IF C000000000106                                                           
              DISPLAY ' EQTRHORI - CALCOLA-RAMO-BILANCIO'                             
           END-IF                                                                     
                                                                                      
           SET C000000000000000000000486 TO TRUE                                      
                                                                                      
           PERFORM VARYING D03370 FROM 1 BY 1       
<snippet>

Section names start with SC and then a series of numbers.
Simalarly copy starts with C, other things with D.

Suggest an alternative where the anonimized mappings are somehow funnier.


# Plan
The implementation must be deterministic so that the same input always maps to the same funny name.
Propose a concrete implementation where there are few schemes available which can be chosen via an input argument passed to the CLI, with one scheme as default.