import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node

def generate_launch_description():

    package_name='mappingbot'
    pkg_share = get_package_share_directory(package_name)
    use_keyboard = LaunchConfiguration('use_keyboard')

    rsp = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    pkg_share,'launch','rsp.launch.py'
                )]), launch_arguments={'use_sim_time': 'true', 'use_ros2_control': 'true'}.items()
    )

    world_path = os.path.join(pkg_share, 'worlds', 'obstacleswall.world')
    # Launch Gazebo Sim (Harmonic)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')]),
        launch_arguments={'gz_args': f'-r {world_path}'}.items()
    )

    # Spawn robot
    spawn_entity = Node(package='ros_gz_sim', executable='create',
                        arguments=['-topic', 'robot_description',
                                   '-name', 'mappingbot',
                                   '-world', 'default',
                                   '-z', '0.1'],
                        output='screen')

    # ROS-GZ Bridge
    bridge_params = os.path.join(pkg_share,'config','ros_gz_bridge.yaml')
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': bridge_params,
            'qos_overrides./tf_static.publisher.durability': 'transient_local',
        }],
        output='screen'
    )

    joystick = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    pkg_share,'launch','joystick.launch.py'
                )]), launch_arguments={
                    'use_sim_time': 'true',
                    'use_keyboard': use_keyboard,
                }.items()
    )

    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_cont",
                   "-p", os.path.join(pkg_share, 'config', 'my_controllers.yaml')],
    )

    # Start diff_cont only after the robot is spawned into Gazebo.
    # The controller manager lives in the Gazebo process and only exists
    # once the spawned robot model initializes its hardware interface.
    diff_after_spawn = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_entity,
            on_exit=[diff_drive_spawner],
        )
    )

    joint_broad_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_broad"],
    )

    # Start joint_broad only after the diff_cont spawner exits.
    # The two spawners share one inter-process lock; starting them
    # together lets one starve the other (5 failed lock attempts then
    # exit 1), leaving a controller permanently unloaded.
    joint_broad_after_diff_cont = RegisterEventHandler(
        OnProcessExit(
            target_action=diff_drive_spawner,
            on_exit=[joint_broad_spawner],
        )
    )

    twist_mux_params = os.path.join(pkg_share,'config','twist_mux.yaml')
    twist_mux = Node(
            package="twist_mux",
            executable="twist_mux",
            parameters=[twist_mux_params, {'use_sim_time': True}],
            remappings=[('cmd_vel_out','/diff_cont/cmd_vel')]
        )

    # SLAM Toolbox, started after both controllers are up so that
    # odometry, TF, and laser data are already flowing.
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            pkg_share, 'launch', 'online_async_launch.py'
        )]), launch_arguments={'use_sim_time': 'true'}.items()
    )

    slam_after_controllers = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_broad_spawner,
            on_exit=[slam],
        )
    )

    # Nav2
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            pkg_share, 'launch', 'navigation_launch.py'
        )]), launch_arguments={'use_sim_time': 'true'}.items()
    )

    # Nav2, started after the controllers for the same reason: its
    # costmaps fail activation (and the lifecycle manager aborts the
    # whole bringup) if the odom transform is not yet available.
    nav2_after_controllers = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_broad_spawner,
            on_exit=[nav2],
        )
    )

    # RViz
    rviz_config_file = os.path.join(pkg_share, 'config', 'view_bot.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': True}]
    )

    # Launch them all!
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_keyboard',
            default_value='false',
            description='Launch keyboard teleoperation if true'),
        rsp,
        gazebo,
        spawn_entity,
        ros_gz_bridge,
        joystick,
        twist_mux,
        diff_after_spawn,
        joint_broad_after_diff_cont,
        slam_after_controllers,
        nav2_after_controllers,
        TimerAction(period=5.0, actions=[rviz_node]) # Delay rviz
    ])
