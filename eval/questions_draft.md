# Întrebări de evaluare — ciornă v0

Scop: întrebările la care asistentul TREBUIE să știe să răspundă. Din ele alegem
documentele și construim setul de evaluare (Faza 3).

Reguli:
- Întrebările se scriu ÎNAINTE de a construi RAG-ul și nu se mai modifică după ce vedem
  rezultatele (altfel evaluarea devine prea optimistă, aceeași problemă ca la licență).
- Fiecare întrebare are sursa așteptată. Răspunsul de referință îl completăm citind
  documentul, nu din memorie.
- Sunt în engleză, ca documentele. Întrebări în română testăm separat, mai târziu.

## A. Autentificare și parole
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 1 | How should user passwords be stored, and which hashing algorithms are recommended? | Password Storage CS |
| 2 | What minimum password length does NIST recommend when a password is the only authentication factor? | NIST SP 800-63B-4 |
| 3 | Should applications force users to change their passwords periodically? | NIST SP 800-63B-4 |
| 4 | Which multi-factor authentication methods are considered phishing-resistant? | NIST SP 800-63B-4, MFA CS |
| 5 | How should a secure "forgot password" flow be designed? | Forgot Password CS |

## B. Sesiuni și token-uri
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 6 | What must a server validate when it receives a JWT? | JWT CS, ASVS V9 |
| 7 | How can an application protect itself against the JWT "none" algorithm attack? | JWT CS |
| 8 | Which attributes should be set on session cookies? | Session Management CS |
| 9 | How can a web application protect against CSRF? | CSRF Prevention CS |

## C. Autorizare și API-uri
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 10 | What is broken access control? Give typical examples. | Top 10 A01:2025 |
| 11 | How should authorization checks be implemented in an API? | Authorization CS, REST Security CS |
| 12 | How can a GraphQL API be protected against very expensive or deeply nested queries? | GraphQL CS |
| 13 | How should file uploads be validated and stored securely? | File Upload CS |

## D. Injection și validare
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 14 | What is the primary defense against SQL injection? | SQL Injection Prevention CS, Top 10 A05:2025 |
| 15 | What is the difference between allowlist and denylist input validation, and which is preferred? | Input Validation CS |
| 16 | How does output encoding help prevent XSS? | XSS Prevention CS |

## E. Erori, logging, secrete, supply chain
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 17 | What information should never be written to application logs? | Logging CS |
| 18 | What error details should be returned to API clients? | Error Handling CS, Top 10 A10:2025 |
| 19 | Where and how should API keys and other secrets be stored? | Secrets Management CS |
| 20 | What is "Software Supply Chain Failures" in the OWASP Top 10:2025? | Top 10 A03:2025 |

## F. Căutare după ID (calea structurată, nu RAG)
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 21 | What does ASVS requirement V6.2.1 require? | ASVS CSV (lookup) |
| 22 | What is A07:2025 in the OWASP Top 10? | Top 10 (lookup) |

## G. Întrebări FĂRĂ răspuns în documente (asistentul trebuie să refuze)
| # | Întrebare | Comportament așteptat |
|---|---|---|
| 23 | How do I configure Group Policy to harden Windows Server 2022? | „Nu am găsit în documente” |
| 24 | Which antivirus product has the best detection rate? | „Nu am găsit în documente” |
| 25 | What is the CVSS score of CVE-2024-3094? | Mai târziu: unealta NVD. Acum: refuz |

## De făcut
- [ ] Citește întrebările: ce lipsește din ce ai vrea să știe asistentul?
- [ ] Mai adaugă 5–10 întrebări (mai ales din experiența ta: ASP.NET, JWT, GraphQL).
- [ ] Ajungem la cel puțin 40 de întrebări cu răspuns + 10 fără răspuns.
