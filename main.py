"""CLI entrypoint for the daily show trace pipeline."""

import argparse
from app.pipeline import init_profile_from_subscription, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="演出活动监控")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="跳过真实抓取，从 data/fixtures/ 读预置 HTML（用于验证抽取链路）",
    )
    parser.add_argument(
        "--init-profile",
        action="store_true",
        help="开 GUI Chrome 让你手动浏览一次大麦，养 .browser-profile/（首次必跑）",
    )
    args = parser.parse_args()

    if args.init_profile:
        init_profile_from_subscription()
        return

    result = run_pipeline(use_fixture=args.fixture, notify=True, trigger="cli")
    print(f"\n=== run #{result.get('run_id')} status={result['status']} ===")


if __name__ == "__main__":
    main()
