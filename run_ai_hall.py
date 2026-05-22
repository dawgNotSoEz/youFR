import os
import sys
from pathlib import Path

# Enable ANSI escape sequences on Windows
os.system('')

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_hall.app import run
from ai_hall.pipeline.types import VerificationState

def format_beautiful_output(out):
    # ANSI escape sequences for premium colors
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    print("\n" + "=" * 80)
    print(f"🛡️  {BOLD}{CYAN}AI HALL FACTUAL VERIFICATION REPORT{RESET}")
    print(f"   {BOLD}Run ID:{RESET} {out.run_id}")
    print("=" * 80)
    
    # 1. Original Generation
    print(f"\n{BOLD}🤖 Original LLM Generation:{RESET}")
    print(f"  \"{out.generation.answer_text.strip()}\"")
    
    # 2. Extracted Claims Analysis
    print(f"\n{BOLD}🔍 Extracted Factual Claims:{RESET}")
    if not out.claims:
        print(f"  {YELLOW}No factual claims extracted.{RESET}")
    else:
        for idx, analysis in enumerate(out.analyses, 1):
            claim = analysis.claim
            state = analysis.verification.state
            conf = analysis.confidence
            
            # Emojis & Colors based on state
            if state == VerificationState.TRUE:
                state_str = f"{GREEN}✅ TRUE{RESET}"
            elif state in {VerificationState.FALSE, VerificationState.CONFLICTING_EVIDENCE}:
                state_str = f"{RED}❌ {state.value}{RESET}"
            else:
                state_str = f"{YELLOW}⚠️ {state.value}{RESET}"
                
            conf_color = GREEN if conf >= 80 else (YELLOW if conf >= 50 else RED)
            
            print(f"\n  {BOLD}[Claim #{idx}]{RESET} \"{claim.text}\"")
            print(f"  ├─ {BOLD}Verification:{RESET} {state_str}")
            print(f"  ├─ {BOLD}Confidence:{RESET} {conf_color}{conf}%{RESET}")
            
            if analysis.explanation:
                print(f"  ├─ {BOLD}Explanation:{RESET} {analysis.explanation.explanation_text}")
                if analysis.explanation.suggested_correction:
                    print(f"  └─ {BOLD}Suggested Correction:{RESET} {analysis.explanation.suggested_correction}")
                else:
                    print(f"  └─ {BOLD}No correction needed.{RESET}")
            else:
                print(f"  └─ {BOLD}No explanation generated.{RESET}")
                
    # 3. Corrected Answer
    if out.corrected_answer:
        print(f"\n{BOLD}🛡️  Shielded / Corrected Answer:{RESET}")
        print(f"  {GREEN}\"{out.corrected_answer.strip()}\"{RESET}")
    
    # 4. Summary & Trust Report
    summary = out.summary
    gate_passed = summary.hard_gate_passed
    gate_str = f"{GREEN}PASS{RESET}" if gate_passed else f"{RED}FAIL{RESET}"
    
    risk = summary.risk_level
    if risk in {"CRITICAL", "HIGH"}:
        risk_str = f"{RED}{BOLD}{risk}{RESET}"
    elif risk == "MEDIUM":
        risk_str = f"{YELLOW}{BOLD}{risk}{RESET}"
    else:
        risk_str = f"{GREEN}{BOLD}{risk}{RESET}"
        
    reliability = summary.overall_reliability
    rel_color = GREEN if reliability >= 80 else (YELLOW if reliability >= 50 else RED)
    
    print("\n" + "-" * 80)
    print(f"{BOLD}📊 OVERALL TRUST METRICS:{RESET}")
    print(f"  ├─ {BOLD}Factual Reliability:{RESET} {rel_color}{reliability}%{RESET}")
    print(f"  ├─ {BOLD}Safety Gate:{RESET} {gate_str}")
    print(f"  ├─ {BOLD}Risk Level:{RESET} {risk_str}")
    print(f"  └─ {BOLD}Verdict:{RESET} {summary.reason}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    # If args are passed, run once and exit with raw JSON
    args = sys.argv[1:]
    if args:
        q = " ".join(args).strip()
        out = run(q)
        print(out.model_dump_json(indent=2))
    else:
        print("=" * 80)
        print(f"🛡️  {BOLD}{CYAN}AI Hall: Interactive Factual Truth Layer Shell{RESET}")
        print("=" * 80)
        print("Enter a factual statement or question to verify.")
        print("To exit, press [Enter] on an empty line, or type 'exit' / 'quit'.\n")
        
        while True:
            try:
                q = input(f"{BOLD}AI Hall > {RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{BOLD}Goodbye!{RESET}")
                break
                
            if not q or q.lower() in {"exit", "quit"}:
                print(f"{BOLD}Exiting. Goodbye!{RESET}")
                break
                
            print(f"\n🔍 {CYAN}Analyzing claim and verifying truth offline...{RESET}")
            try:
                out = run(q)
                format_beautiful_output(out)
            except Exception as e:
                print(f"❌ {BOLD}Error during verification:{RESET} {e}\n")
