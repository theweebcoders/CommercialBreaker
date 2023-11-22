import argparse
from GUI import TOM, CommercialBreaker
from CLI import clydes

def main():
    parser = argparse.ArgumentParser(description="Run different parts of the application.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--tom', action='store_true', help="Run the GUI interface (TOM)")
    group.add_argument('--clydes', action='store_true', help="Run the CLI interface")
    group.add_argument('--combreak', action='store_true', help="Run the standalone Commercial Breaker GUI")

    args = parser.parse_args()

    if args.tom:
        TOM()  # Replace 'run()' with the actual function to start the GUI from TOM
    elif args.clydes:
        clydes()  # Replace 'run()' with the actual function to start the CLI
    elif args.combreak:
        CommercialBreaker()  # Replace 'run()' with the actual function to start Commercial Breaker

if __name__ == "__main__":
    main()
