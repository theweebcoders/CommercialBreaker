import argparse
from GUI import TOM, CommercialBreaker, Absolution
from CLI import clydes, CommercialBreakerCLI

def main():
    parser = argparse.ArgumentParser(description="Run different parts of the application.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--tom', action='store_true', help="Run the GUI interface (TOM)")
    group.add_argument('--clydes', action='store_true', help="Run the CLI interface")
    group.add_argument('--combreak', action='store_true', help="Run the standalone Commercial Breaker GUI")
    group.add_argument('--webui', action='store_true', help="Run the web interface")
    group.add_argument('--combreakcli', action='store_true', help="Run the CLI interface for the Commercial Breaker")
    parser.add_argument('--use_message_broker', action='store_true', help="Use message broker for inter-component communication")
    parser.add_argument('--docker', action='store_true', help="Do not use this unless you are running the application in a Docker container")
    parser.add_argument('--cutless', action='store_true', help="Enable Cutless Mode feature in the application")
    args = parser.parse_args()

    # Set TOM as default if no other interface is specified
    if not any([args.clydes, args.combreak, args.webui, args.combreakcli]):
        args.tom = True

    if args.tom:
        TOM()
    elif args.clydes:
        clydes()
    elif args.combreak:
        CommercialBreaker()
    elif args.webui:
        Absolution()
    elif args.combreakcli:
        CommercialBreakerCLI()

if __name__ == "__main__":
    main()