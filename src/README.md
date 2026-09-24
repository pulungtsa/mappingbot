## Robot Package Template

This is a GitHub template. You can make your own copy by clicking the green "Use this template" button.

It is recommended that you keep the repo/package name the same, but if you do change it, ensure you do a "Find all" using your IDE (or the built-in GitHub IDE by hitting the `.` key) and rename all instances of `mappingbot` to whatever your project's name is.

Note that each directory currently has at least one file in it to ensure that git tracks the files (and, consequently, that a fresh clone has direcctories present for CMake to find). These example files can be removed if required (and the directories can be removed if `CMakeLists.txt` is adjusted accordingly).

## Simulation launch notes

Both entry points start the same complete stack (`launch_sim.launch.py`
is a thin wrapper around `unified_sim.launch.py`):

    ros2 launch mappingbot launch_sim.launch.py
    ros2 launch mappingbot unified_sim.launch.py   # add use_keyboard:=true for keyboard teleop

Always start from a clean process state. Stale processes from a previous
run (especially a second `parameter_bridge`) create a duplicate `/clock`
publisher, which causes simulation-time jumps, TF buffer clears, SLAM
message-filter overflow, and Nav2/RViz resets. Never run two simulation
launches concurrently. Clean up leftovers with:

    pkill -9 -f "gz-sim|parameter_bridge|robot_state_publisher|slam_toolbox|nav2_|rviz2|joy_node|teleop|twist_mux|twist_stamper|controller_manager/spawner|launch mappingbot"

The two controller spawners run sequentially (joint_broad starts after
the diff_cont spawner exits) because they share one inter-process lock;
starting them together can leave one controller permanently unloaded.
If a spawner still cannot reach the controller manager (DDS discovery
flake), load it manually without changing any file::

    ros2 service call /controller_manager/load_controller controller_manager_msgs/srv/LoadController "{name: <ctrl>}"
    ros2 service call /controller_manager/configure_controller controller_manager_msgs/srv/ConfigureController "{name: <ctrl>}"
    ros2 service call /controller_manager/switch_controller controller_manager_msgs/srv/SwitchController "{activate_controllers: [<ctrl>], strictness: 2}"

Prefer SIGTERM over SIGKILL when stopping the stack: `kill -9` leaves
FastDDS shared-memory segments (`/dev/shm/fastdds_*`) and undisposed
participants behind, and accumulated cruft makes new same-named nodes
(e.g. bt_navigator) wedge silently at startup with zero log output.
If nodes start hanging pre-banner, stop everything and clear stale
segments before relaunching:

    rm -f /dev/shm/fastdds_*