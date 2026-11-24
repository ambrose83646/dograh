# Transcript storage time check

Service: `https://submission-stranger-displays-sends.trycloudflare.com`

- **PASS** Before the deletion, the words of the first call are in the answer to the assistant, in the file and in the database row  
  call 186: 573 characters; {'file_status': 200, 'words_in_file': True, 'words_in_row': True}
- **PASS** The deletion removes the words of the old call from the answer to the assistant, the file and the database row  
  deleted 1 calls, call 186 included: True; {'file_status': 404, 'words_in_file': False, 'words_in_row': False, 'sentences_checked': 6, 'sentences_in_row': []}
- **PASS** The assistant is told that the words were deleted, and is not told to wait for them  
  The words of this call were deleted, because the call is older than 30 days. `result` has what is left. Do not ask again.
- **PASS** The other data of the old call stays: status, length, numbers, task, result, the list of calls, the minutes used  
  changed fields: none; result: {'task_completed': False, 'outcome_summary': 'The caller began asking on behalf of Lena Fi; minutes used 0.9 before
- **PASS** A call that is not old keeps its words  
  call 187 started after the age limit; deleted: False
- **PASS** A deletion during a call does not touch that call: the call continues and its words are stored at the end  
  call 187 during the deletion: in_progress; after the end: 725 characters; {'file_status': 200, 'words_in_file': True, 'words_in_row': True}
- **PASS** When the second call is old, a new deletion removes its words too  
  {'file_status': 404, 'words_in_file': False, 'words_in_row': False}
- **PASS** A deletion that finds nothing more to do reports no call  
  calls reported by the last deletion: []
- **PASS** No completed call of any account in the database keeps words (the deletion did all groups of calls)  
  0 completed calls with a transcript file or word events
