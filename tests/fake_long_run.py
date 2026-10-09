"""pgg_game.main with a fake, slow OpenRouter client: a stand-in run process (task #80).

    python tests/fake_long_run.py <pgg_game.py options>

Used by test_runctl.py as `runctl.py start --entry tests/fake_long_run.py`:
the real CLI, Engine, status.json, heartbeat and signal handling run in their
own process, every API call is answered by test_pgg_guards.CostAPI after
FAKE_DELAY_S seconds (environment, default 0.2). No network, no ../.env, no
key (test_pgg_game sets a dummy one before importing llm_client). Not a test
module (its name does not start with test_).
"""

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_guards import CostAPI  # noqa: E402  (dummy key, llm_client imported)

import llm_client  # noqa: E402
import pgg_game  # noqa: E402


def main(argv) -> int:
    delay = float(os.environ.get("FAKE_DELAY_S", "0.2"))
    api = CostAPI(cost=0.001)

    def create(**kwargs):
        time.sleep(delay)
        return api(**kwargs)

    llm_client._client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create)))
    pgg_game._REQUIRE_VERIFIED_CODE = False    # the test's code may be uncommitted
    return pgg_game.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
