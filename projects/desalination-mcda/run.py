"""Reproducible small run of the original MCDA model."""
import argparse
from pathlib import Path
import model

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=model.DEFAULT_COMMUNITY_INPUT_CSV)
    parser.add_argument('--parameters', type=int, default=20)
    parser.add_argument('--weights', type=int, default=50)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--output', type=Path, default=Path('output'))
    args = parser.parse_args()
    if args.parameters < 1 or args.weights < 1:
        parser.error('Sample counts must be positive.')
    result = model.analyze_community_dataset(args.inputs, args.parameters, args.weights, args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    result['results'].to_csv(args.output / 'results.csv', index=False)
    result['current_winners'].to_csv(args.output / 'baseline.csv', index=False)
    print(result['current_winners'].to_string(index=False))

if __name__ == '__main__':
    main()
