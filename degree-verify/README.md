# 🎓 Degree Verification — FY Project

## Files (4 total)
```
DegreeVerification.sol  ← smart contract
app.py                  ← flask backend + UI (all in one)
test_system.py          ← 5 test cases
requirements.txt
```

## Run it
```bash
pip install -r requirements.txt
npx ganache --port 7545        # terminal 1
python app.py                  # terminal 2
# open http://127.0.0.1:5000
```

## Test it
```bash
python test_system.py          # terminal 3 (while app.py is running)
```

## How it works
1. University uploads PDF → SHA-256 hash → stored on Ganache blockchain
2. Employer uploads same PDF → hash computed → checked against blockchain
3. Tampered PDF → different hash → not found → INVALID

## Viva answers
**Why blockchain?** Immutable — once written, no one can alter the record without the whole network detecting it.

**Why SHA-256?** Deterministic one-way function. Same file = same hash every time. Change one byte = completely different hash (avalanche effect).

**Why not store the PDF on-chain?** Storing raw files on Ethereum costs enormous gas. Only the 32-byte fingerprint is stored.

**What does `onlyOwner` do?** Solidity modifier — reverts the transaction if the caller is not the deploying wallet. Prevents anyone else from issuing degrees.

**What is a `view` function?** Read-only — does not change state, costs zero gas when called externally.
