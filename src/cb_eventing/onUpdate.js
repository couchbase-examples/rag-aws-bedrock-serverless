function OnUpdate(doc, meta) {
    if (doc.hasOwnProperty('embedding')) {
        log("Embedding exists in the document, skipping API call.");
        return;
    }

    // Prepare the data to send to API Gateway
    let payload = {
        ...doc,
        id: meta.id,
    };

    try {
        // Make the HTTP POST request to API Gateway
        let response = curl("POST", apiUrl,
            {
                body: JSON.stringify(payload),
                headers: {
                    "Content-Type": "application/json",
                }
            }
        );

        // Log the response
        log("API Gateway response: ");
        log(response)
    } catch (e) {
        // Log any errors
        log("Error calling API Gateway: ");
        log(e)
    }
}