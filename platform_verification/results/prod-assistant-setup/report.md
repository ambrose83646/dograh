# Assistant-led setup, end_call and billing link check

Service: `https://app.danadial.com`

- **PASS** The instructions name the setup state and the new tools, and do not ask for a key  
  8 tools: ['end_call', 'get_account_status', 'get_billing_link', 'get_call_result', 'list_calls', 'place_call', 'start_caller_id_verification', 'update_settings']
- **PASS** A new account: setup is not complete, the next step is the phone check, and a call is refused  
  state 'verify_phone'; early call: {'refused': 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user 
- **PASS** While the phone rings, setup says to wait for the code and not to start a new check  
  The phone +12085050523 rings. The user must answer and enter the code on the keypad. Then call get_account_status again.
- **PASS** After the code, setup is complete with one phone call: the caller ID is her phone and the account can call  
  state 'ready'; caller ID +12085050523; minutes 10.0
- **PASS** The assistant of a different person cannot end her call  
  his end_call: {'refused': 'Call 122 not found'}; her call after 6 s: in_progress, 59 s
- **PASS** end_call ends the phone call itself in a few seconds (Twilio's own record)  
  Twilio status 'completed' after 2 s; Twilio duration 61 s
- **PASS** The record keeps the words said before the end, and says that the assistant ended the call  
  status completed; ended_by 'assistant'; 719 characters of transcript
- **PASS** The minutes stop at the end of the call  
  1.0 minutes used for a call that was stopped 64 s after the request; 25 s later: 1.0
- **PASS** A second end_call changes nothing  
  {'call_id': 122, 'ended_now': False, 'status': 'completed', 'next_step': 'This call was over already. Nothing changed.'}
- **PASS** end_call on a call that was just started: the phone call ends and the record gets an end  
  end_call 3.0 s after place_call; record 'completed'; Twilio 'canceled', 0 s
- **PASS** That stopped call uses no more than 0.1 call minutes  
  minutes used before 1.0, after 1.0
- **PASS** get_billing_link gives the billing page and how she signs in  
  https://danadial.com/dashboard/billing; The user signs in on that page with the phone +12085050523: the page sends a code by text 
- **PASS** With the free minutes used, setup says that calls are blocked and that she needs the plan; a call is refused  
  The 0 free call minutes are used. The user must start the monthly plan at https://danadial.com/dashboard/billing before this account can make more cal
- **PASS** Outbound only: the instructions, the tools, and the tool answers do not speak of inbound calls, and an inbound tool does not run  
  21 texts read; inbound words found: none; set_inbound_rules: {'refused': "Unknown tool: 'set_inbound_rules'"}
