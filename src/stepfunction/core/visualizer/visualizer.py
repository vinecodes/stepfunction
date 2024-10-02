""" This module contains the visualizer class for the graph model.

    Author: Vineeth Penugonda
"""

from os import getcwd

from graphviz import Digraph

from stepfunction.constants.visualizer import (
    DEFAULT_VISUALIZER_EXTENSION, DEFAULT_VISUALIZER_FAILURE_EDGE_COLOR,
    DEFAULT_VISUALIZER_FAILURE_EDGE_LABEL, DEFAULT_VISUALIZER_FOLDER,
    DEFAULT_VISUALIZER_FORMAT, DEFAULT_VISUALIZER_PARALLEL_STEP_EDGE_STYLE,
    DEFAULT_VISUALIZER_RENDERER, DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_COLOR,
    DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_LABEL,
    DEFAULT_VISUALIZER_STRING_ENCODING,
    DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_NODE_SHAPE,
    DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_NODE_STYLE,
    DEFAULT_VISUALIZER_SUCCESS_EDGE_LABEL)
from stepfunction.types.step_types import StepParams
from stepfunction.types.visualizer_types import RenderStepFunctionParams


class Visualizer:
    """ This class is responsible for visualizing the graph model.
    """

    def __init__(self, graph_name: str, steps: StepParams = None):
        """ Initializes the visualizer."""

        self.graph_name = graph_name
        self.__steps = steps

        self.__output_file_name = None
        self.__output_file_path = None

        self.__dot = Digraph(comment=self.graph_name)

    def visualize_step_function(self):
        """ Visualizes the graph model.
        """

        if not self.__steps:
            raise ValueError("No steps found to visualize.")

        for step_name, step_info in self.__steps.items():

            if 'is_sub_step_function' in step_info and step_info['is_sub_step_function']:
                self.__dot.node(step_name, step_name, shape=DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_NODE_SHAPE,
                                style=DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_NODE_STYLE)
            else:
                self.__dot.node(step_name, step_name)

            if step_info['next_step']:
                self.__dot.edge(
                    step_name, step_info['next_step'], label=DEFAULT_VISUALIZER_SUCCESS_EDGE_LABEL)

            if step_info['on_failure']:
                failure_edge_label = DEFAULT_VISUALIZER_FAILURE_EDGE_LABEL
                failure_edge_color = DEFAULT_VISUALIZER_FAILURE_EDGE_COLOR

                if step_info.get('stop_on_failure'):
                    failure_edge_label = DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_LABEL
                    failure_edge_color = DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_COLOR

                self.__dot.edge(
                    step_name, step_info['on_failure'], label=failure_edge_label, color=failure_edge_color)

            if step_info['parallel']:

                # func is a dictionary for parallel steps
                parallel_function_names = step_info['func']

                with self.__dot.subgraph() as s:
                    s.attr(rank='same')

                    for parallel_step_name, func in parallel_function_names.items():
                        self.__dot.node(parallel_step_name, parallel_step_name)
                        self.__dot.edge(
                            step_name, parallel_step_name, style=DEFAULT_VISUALIZER_PARALLEL_STEP_EDGE_STYLE)

                        if step_info['next_step']:
                            self.__dot.edge(parallel_step_name,
                                            step_info['next_step'])

            if step_info.get('branch'):
                for result, next_step in step_info['branch'].items():
                    self.__dot.edge(step_name, next_step,
                                    label=f"Branch: {result}")

    def render_step_function(self, **kwargs: RenderStepFunctionParams):
        """ Renders the graph model.
        """
        current_dir = getcwd()

        format = kwargs.get('format', DEFAULT_VISUALIZER_FORMAT)
        renderer = kwargs.get('renderer', DEFAULT_VISUALIZER_RENDERER)

        file_path = kwargs.get(
            'file_path', f"{current_dir}/{DEFAULT_VISUALIZER_FOLDER}")
        file_name = kwargs.get('file_name', f"{self.graph_name}.{
                               DEFAULT_VISUALIZER_EXTENSION}")

        self.__output_file_path = file_path
        self.__output_file_name = file_name

        self.__dot.render(
            filename=f"{self.__output_file_path}/{self.__output_file_name}", format=format, renderer=renderer)

    def render_step_function_to_string(self, **kwargs: RenderStepFunctionParams):
        """ Renders the graph model as a string.
        """

        format = kwargs.get('format', DEFAULT_VISUALIZER_FORMAT)
        renderer = kwargs.get('renderer', DEFAULT_VISUALIZER_RENDERER)

        return self.__dot.pipe(format=format, renderer=renderer).decode(DEFAULT_VISUALIZER_STRING_ENCODING)

    @property
    def output_file_name(self):
        """ Returns the output file name.
        """
        return self.__output_file_name

    @property
    def output_file_path(self):
        """ Returns the output file path.
        """
        return self.__output_file_path
