import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_share = get_package_share_directory('mappingbot')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_keyboard',
            default_value='false',
            description='Launch keyboard teleoperation if true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                pkg_share, 'launch', 'unified_sim.launch.py')]),
            launch_arguments={
                'use_keyboard': LaunchConfiguration('use_keyboard'),
            }.items()
        ),
    ])