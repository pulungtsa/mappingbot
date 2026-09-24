from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition

import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_keyboard = LaunchConfiguration('use_keyboard')

    joy_params = os.path.join(get_package_share_directory('mappingbot'),'config','joystick.yaml')

    joy_node = Node(
            package='joy',
            executable='joy_node',
            parameters=[joy_params, {'use_sim_time': use_sim_time}],
         )

    teleop_node = Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_node',
            parameters=[joy_params, {'use_sim_time': use_sim_time}],
            remappings=[('/cmd_vel','/cmd_vel_joy')]
         )

    twist_stamper = Node(
            package='twist_stamper',
            executable='twist_stamper',
            parameters=[{'use_sim_time': use_sim_time}],
            remappings=[('cmd_vel_in', '/cmd_vel_joy'),
                        ('cmd_vel_out', '/cmd_vel_joy_stamped')]
         )

    keyboard_node = Node(
            package='teleop_twist_keyboard',
            executable='teleop_twist_keyboard',
            name='keyboard_teleop',
            remappings=[('cmd_vel', '/cmd_vel_joy')],
            prefix='bash -c \'exec "$1" "${@:2}" < /dev/tty\' --',
            emulate_tty=True,
            condition=IfCondition(use_keyboard)
         )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use sim time if true'),
        DeclareLaunchArgument(
            'use_keyboard',
            default_value='false',
            description='Launch keyboard teleoperation if true'),
        joy_node,
        teleop_node,
        twist_stamper,
        keyboard_node
    ])
