''' Build for learing/testing purpose. Build by Dragan Vasic with great help from Claude '''

import random
from datetime import date
from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("fruit-for-dinner")


FRUITS = ["Banana", "Apple", "Orange", "Pear", "Mango", "Plum", "Cherry"]


@mcp.tool(
    description=(
        "Generate suggestion for fruit dinner. "
        "Date can be send as a parameter, not required, it can be NONE"
    )
)
def fruit_for_dinner(
    date: Annotated[Optional[date], Field(description="Date or None")] = None,
):
    index = random.randint(0, len(FRUITS) - 1)
    if date is not None:
        index = date.day % len(FRUITS)
    return FRUITS[index]


if __name__ == "__main__":
    mcp.run()
