# Account join and clean-up check

Service: `https://gbp-moms-above-saver.trycloudflare.com`

- **PASS** Maria has a web site account with a plan and no caller ID  
  account 500060; plan HTTP 200
- **PASS** "Allow" makes a new account that does not see her plan  
  new account 500061; plan None
- **PASS** An account with its own sign-in cannot start a check of her phone number  
  HTTP 409: {"detail":"This phone number belongs to another account. One phone number can be used on one account only."}
- **PASS** The start of a check and a wrong code on the phone give no access: the assistant stays on the empty account  
  plan None; caller ID None
- **PASS** After one phone check, the assistant works for her first account: it reads her plan and her caller ID  
  plan 'Join check plan'; caller ID '+12088864742'
- **PASS** The same phone call gave her first account its caller ID, so she is not phoned a second time  
  web site view: caller ID '+12088864742'
- **PASS** The empty account is closed: its Twilio subaccount is not open, and it is not in the list of assistant accounts  
  open subaccounts of 500061: 0
- **PASS** A refresh after the join gives a token of her first account  
  refresh HTTP 200; plan 'Join check plan'
- **PASS** A second assistant joins the same account with one phone check, and her caller ID stays as it was  
  second account 500063; plan 'Join check plan'
- **PASS** The first assistant still works after the second one joined  
  plan 'Join check plan'
- **PASS** The timed clean-up does not remove an account that is new  
  removed by the timed clean-up: []
- **PASS** The clean-up removes an old account with no phone: its tokens stop and its Twilio subaccount is closed  
  removed: [500040, 500041, 500042, 500043, 500045, 500046, 500047, 500049, 500050, 500051, 500052, 500053, 500058, 500064]; Omar's token connects: False; refresh HTTP 401
- **PASS** The clean-up keeps an account with a verified phone and an account that a person paid for  
  Maria's caller ID '+12088864742'; Priya's account 500065 is open
