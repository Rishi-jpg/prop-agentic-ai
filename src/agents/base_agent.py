import json
from typing import Any, Optional
from fastmcp import Client, FastMCP
from pydantic import BaseModel, Field

from src.llm.base import LLMProvider, Message

class AgentResult(BaseModel):
    agent_name:str
    response:str
    tool_calls_made: list[dict[str, Any]] = Field(default_factory=list)
    total_tokens: int = 0

def _mcp_to_bedrock_tools(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Convert FastMCP tool definitions into Amazon Bedrock Converse toolSpec format."""
    bedrock_tools = []
    for tool in mcp_tools:
        bedrock_tools.append({
            "toolSpec": {
                "name": tool.name,
                "description": tool.description or f"Execute {tool.name}",
                "inputSchema": {"json": tool.input_schema}
            }
        })
    return bedrock_tools


class MCPAgent:
    """
    An AI agent that can communicate with an LLM
    and use external tools through an MCP server.
    """
    def __init__(self,name,system_prompt,llm,mcp_server=None,max_steps=5):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm
        self.mcp_server = mcp_server
        self.max_steps = max_steps
    
    async def run(self, user_input, history=None):

        #conversation history
        messages = history.copy() if history else []
        messages.append(
            Message(role="user", content=user_input)
        )
        total_tokens = 0
        tool_calls = []

        # Agent has no MCP Server
        if self.mcp_server is None:

            response = await self.llm.generate(
                messages=messages,
                system_prompt=self.system_prompt
            )

            return AgentResult(
                agent_name=self.name,
                response=response.content,
                total_tokens=(
                    response.input_tokens +
                    response.output_tokens
                )
            )
        
        #Connect to MCP server
        async with Client(self.mcp_server) as client:

            #available tools
            available_tools = await client.list_tools()

            # Convert MCP tools into the format
            # expected by our LLM provider
            llm_tools = _mcp_to_bedrock_tools(available_tools)

            #Start the agent's decision loop
            for step in range(self.max_steps):

                response = await self.llm.generate(
                    messages=messages,
                    system_prompt=self.system_prompt,
                    tools=llm_tools
                )

                total_tokens += (
                    response.input_tokens +
                    response.output_tokens
                )

                #Check whether the LLM wants to execute any tools
                if not response.tool_calls:

                    return AgentResult(
                        agent_name=self.name,
                        response=response.content,
                        tool_calls_made=tool_calls,
                        total_tokens=total_tokens
                    )

                #Save the LLM's tool request
                messages.append(
                    Message(
                        role="assistant",
                        content=response.content,
                        tool_calls=response.tool_calls
                    )
                )

                #Execute the requested tools
                for tool_call in response.tool_calls:

                    result = await client.call_tool(
                        tool_call.name,
                        tool_call.arguments
                    )

                    # Extract tool response
                    tool_output = result.content[0].text if result.content else "{}"

                    # Parse JSON for structured logging/inspection
                    try:
                        parsed_output = json.loads(tool_output)
                    except json.JSONDecodeError:
                        parsed_output = tool_output

                    tool_calls.append({
                        "tool": tool_call.name,
                        "arguments": tool_call.arguments,
                        "output": parsed_output,
                    })

                    #Send tool result back to LLM
                    messages.append(
                        Message(
                            role="tool",
                            content=tool_output,
                            tool_call_id=tool_call.id
                        )
                    )

        #Stop if maximum steps are reached
        return AgentResult(
            agent_name=self.name,
            response=(
                "I couldn't complete the request "
                "within the allowed tool execution steps."
            ),
            tool_calls_made=tool_calls,
            total_tokens=total_tokens
        )
