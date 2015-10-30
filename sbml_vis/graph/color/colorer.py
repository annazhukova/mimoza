__author__ = 'anna'

from sbml_vis.graph.graph_properties import TYPE_BG_SPECIES, TYPE_BG_REACTION, TYPE_BG_COMPARTMENT

GREY = "#B4B4B4"

ORANGE = "#EDB337"

YELLOW = "#F0DA78"

RED = "#E37B6F"

BLUE = "#79A8C9"

GREEN = "#B1C95B"

VIOLET = "#A595BF"

TURQUOISE = "#76C29B"

WHITE = 'white'


def get_edge_color(ubiquitous, generalized, transport, color=None):
    if ubiquitous:
        return GREY
    if color:
        return color
    if generalized:
        return TURQUOISE if transport else GREEN
    return VIOLET if transport else BLUE


def get_bg_color(node_type, transport, color=None):
    if TYPE_BG_SPECIES == node_type:
        if color:
            return color
        return ORANGE
    if TYPE_BG_REACTION == node_type:
        if color:
            return color
        return TURQUOISE if transport else GREEN
    if TYPE_BG_COMPARTMENT == node_type:
        if color:
            return color
        return YELLOW
    return None


def get_species_color(ubiquitous, generalized, color=None):
    if color:
        return color
    return ORANGE if generalized else (GREY if ubiquitous else RED)


def get_reaction_color(generalized, transport, color=None):
    if color:
        return color
    if generalized:
        return TURQUOISE if transport else GREEN
    return VIOLET if transport else BLUE


def get_compartment_color(color=None):
    if color:
        return color
    return YELLOW