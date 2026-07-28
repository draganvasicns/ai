''' Build for learing/testing purpose. Build by Dragan Vasic with great help from Claude '''

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field
import random

mcp = FastMCP("random-name-server")


class Gender(StrEnum):
    MALE = "Male"
    FEMALE = "Female"


MALE_FIRST_NAMES= ["Dragan","Milan","Marko","Pera","Nikola","Djorjde","Milojko"]
FEMALE_FIRST_NAMES = ["Vesna", "Jovana","Biljana","Brankica","Milana","Jelena"]
LAST_NAMES=["Vasic","Jovicic","Milenkovic","Keselj","Cvarkov","Adzic","Peckov"]


@mcp.tool(
    description=(
        "Generate random First names for people. " \
        "Result could be Dragan, Milan, Vesna etc. " \
        "In argument we define gender - Male or Female. " \
        "Depending of gender we retun name for male or female"
    )
)
def random_first_name (
    gender: Annotated[Gender, Field(description="Male of Female")]
):
    if gender == Gender.MALE :
        return random.choice(MALE_FIRST_NAMES)
    else:
        return random.choice(FEMALE_FIRST_NAMES)

@mcp.tool(
    description=(
        "Generate random Last names for people. " \
        "Result could be Vasic, Milenkovic etc"
    )
)
def random_last_name (
):
    return random.choice(LAST_NAMES)


@mcp.tool(
    description=(
        "Generate random meanfull full name (FirstName LastName) for people. Radnom first and radnom second name joined. " \
        "Result could be Dragan Vasic, or Milan Jovic etc. " \
        "In argument we define gender - Male or Female. " \
        "Depending of gender we retun name for male or female"
    )
)
def random_full_name(
    gender: Annotated[Gender, Field(description="Male of Female")],
):
    return random_first_name(gender)+ " "+random_last_name()



if __name__ == "__main__":
    mcp.run()
