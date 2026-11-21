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

## G. Din experiența practică (ASP.NET, JWT, GraphQL)
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 23 | How should refresh tokens be protected against replay or theft? | ASVS V10.4.5 |
| 24 | How can a server invalidate a JWT before it expires, for example on logout? | ASVS V7.4.1 |
| 25 | Should GraphQL introspection be enabled in production? | ASVS V4.3.2 |
| 26 | What should a global error handler return to clients, and what should it log? | ASVS V16.5.1, Error Handling CS |
| 27 | How should database credentials and API keys be stored in an ASP.NET application? | ASVS V13.3.1, Secrets Management CS, .NET Security CS |

## H. Atacuri clasice
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 28 | What is an IDOR vulnerability and how is it prevented? | ASVS V8.2.2, Top 10 A01:2025 |
| 29 | What is a mass assignment attack and how can it be prevented? | ASVS V15.3.3 |
| 30 | What is SSRF and how can an application defend against it? | ASVS V1.3.6 |
| 31 | How can an attacker find out which usernames exist, and how is this prevented? | ASVS V6.3.8 |
| 32 | How should an application defend against brute-force and credential stuffing attacks? | ASVS V6.3.1, Authentication CS |

## I. Configurare și browser
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 33 | How should CORS be configured securely? | ASVS V3.4.2 |
| 34 | Is it safe to store tokens or sensitive data in localStorage? | ASVS V14.3.3, JWT CS |
| 35 | Should password rules require uppercase letters, digits and special characters? | ASVS V6.2.5, NIST SP 800-63B-4 |
| 36 | Which TLS versions should be enabled? | ASVS V12.1.1 |

## J. Containere, criptografie, sesiuni, REST
| # | Întrebare | Sursă așteptată |
|---|---|---|
| 37 | Why should a container not run as root, and how can a non-root user be configured? | Docker Security CS (Rule #2, Rule #11) |
| 38 | Where should encryption keys be stored relative to the data they protect? | Cryptographic Storage CS (Key Storage, Separation of Keys and Data) |
| 39 | When should a session ID be regenerated? | Session Management CS (Renew the Session ID After Any Privilege Level Change), ASVS V7.2.4 |
| 40 | Which security headers should a REST API send in its responses? | REST Security CS (Security Headers) |

## K. Întrebări FĂRĂ răspuns în documente (asistentul trebuie să refuze)
Două tipuri: subiecte complet în afara corpusului și „aproape-ratări” (near-miss), care
ating subiecte din documente fără ca documentele să răspundă la întrebare. Cele din urmă
testează dacă asistentul inventează un răspuns pe baza unor fragmente doar asemănătoare.

Verificat prin căutare în `data/raw` (fișierele .md și CSV-ul ASVS; PDF-ul NIST nu a putut
fi căutat ca text). Coloana „Ce există în documente” spune ce ar putea încurca asistentul.

| # | Întrebare | Tip | Ce există în documente | Comportament așteptat |
|---|---|---|---|---|
| 41 | How do I configure Group Policy to harden Windows Server 2022? | în afara corpusului | nimic | „Nu am găsit în documente” |
| 42 | Which antivirus product has the best detection rate? | near-miss | ASVS V5.4.3 și File Upload CS recomandă scanarea cu antivirus, fără produse | Refuz; poate menționa că documentele recomandă doar scanarea |
| 43 | What is the CVSS score of CVE-2024-3094? | în afara corpusului | nimic | Mai târziu: unealta NVD. Acum: refuz |
| 44 | How can I recover files encrypted by ransomware? | near-miss | Top 10 A09 are doar linkuri către ghiduri NIST despre ransomware | Refuz; poate indica referințele din A09 |
| 45 | Which ports does Nmap scan by default? | în afara corpusului | nimic | „Nu am găsit în documente” |
| 46 | How do I secure a home Wi-Fi network with WPA3? | în afara corpusului | Wi-Fi apare doar în treacăt (MFA CS, Session CS) | „Nu am găsit în documente” |
| 47 | Does the npm package lodash 4.17.15 have known vulnerabilities? | în afara corpusului | nimic | Mai târziu: unealta NVD. Acum: refuz |
| 48 | How can prompt injection be prevented in an LLM-based application? | near-miss | Top 10 A05 doar trimite la OWASP LLM Top 10 | Refuz; poate indica OWASP LLM Top 10 |
| 49 | How do I configure SPF, DKIM and DMARC to prevent email spoofing? | în afara corpusului | nimic | „Nu am găsit în documente” |
| 50 | How should a smart contract be audited for reentrancy vulnerabilities? | în afara corpusului | nimic | „Nu am găsit în documente” |

Scoase după verificare (documentele conțin răspunsul, total sau parțial):
- *How do I configure a Kubernetes NetworkPolicy to isolate pods?*: Docker Security CS (Rule #5) recomandă Kubernetes Network Policies.
- *What fines can a company receive under GDPR for a data breach?*: Top 10 A09 (Scenario #3) dă exemplul unei amenzi GDPR de 20 milioane de lire.
- *How do I write AWS IAM policies that follow least privilege?*: Secrets Management CS discută politici IAM fine-grained pentru secrete.

## De făcut
- [ ] Citește întrebările: ce lipsește din ce ai vrea să știe asistentul?
- [x] Mai adaugă 5–10 întrebări (mai ales din experiența ta: ASP.NET, JWT, GraphQL).
- [x] Ajungem la cel puțin 40 de întrebări cu răspuns + 10 fără răspuns.
- [x] Verifică întrebările fără răspuns căutând în documente.
- [ ] După Faza 1 (PyMuPDF): verifică și PDF-ul NIST pentru întrebările 41–50.
