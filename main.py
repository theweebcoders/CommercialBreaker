import argparse
from GUI import TOM, CommercialBreaker
from CLI import clydes, CommercialBreakerCLI

def main():
    parser = argparse.ArgumentParser(description="Run different parts of the application.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--tom', action='store_true', help="Run the GUI interface (TOM)")
    group.add_argument('--clydes', action='store_true', help="Run the CLI interface")
    group.add_argument('--combreak', action='store_true', help="Run the standalone Commercial Breaker GUI")
    group.add_argument('--combreakcli', action='store_true', help="Run the CLI interface for the Commercial Breaker")
    args = parser.parse_args()

    # Default to TOM if no arguments are given
    if not (args.clydes or args.combreak or args.combreakcli):
        args.tom = True

    if args.tom:
        TOM()  # Run the GUI interface for TOM
    elif args.clydes:
        clydes()  # Run the CLI interface
    elif args.combreak:
        CommercialBreaker()  # Run the Commercial Breaker GUI
    elif args.combreakcli:
        CommercialBreakerCLI()

if __name__ == "__main__":
    main()
