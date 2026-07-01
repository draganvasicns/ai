import Anthropic  from "@anthropic-ai/sdk";

const  client = new Anthropic();

const msg =  await client.messages.create({
    model: 'claude-opus-4-8',
    max_tokens: 1024,
    messages: [
        {
            role :'user',
            content: 'Hello, Claude'
        }
    ]
})
console.log(msg);
console.log(JSON.stringify(msg, null, 2));

