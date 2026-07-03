import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const prompt = "What is prompt caching";

const models = ["claude-fable-5","claude-opus-4-8", "claude-sonnet-5"];

console.log(models);

for (const model of models) {
    console.log("Model: " + model);
    let date = new Date();
    const response = await client.messages.create({
            model,
            max_tokens : 300,
            messages: [{
                role: "user", 
                content: prompt
            }]
        });
    const finishTime  = new Date();
    const diff = finishTime.getTime()-date.getTime();
    console.log("Time to respond "+ diff +"ms");
    for (const block of response.content) {
        if (block.type === "text") {
            console.log(block.text);
        }
    }    
}

