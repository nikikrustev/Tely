"""D35: the speed numbers in eval/speed.json are what the bundle gives today."""
import json

from tely.eval import speed


def test_committed_speed_json_is_current():
    old, new = json.loads(speed.OUT.read_text(encoding="utf-8")), speed.run()
    assert old["scheduled"] == new["scheduled"] and old["heard_in_browser"] == new["heard_in_browser"]
    assert new["scheduled"]["goal_to_crowd_roar_s"]["max"] == 0.0     # the roar lands on the reveal itself
