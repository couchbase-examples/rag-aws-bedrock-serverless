function OnUpdate(doc, meta) {
    log("Data")
    log("doc is")
    log(doc)
    log("meta is ")
    log(meta)
    // Check if this is a document we want to proces
        // Prepare the data to send to API Gateway
    let payload = {
        id: meta.id,
        ...doc
    };


    try {
        log(API_KEY)
        request = {
            body: JSON.stringify(payload),
            headers: {
                "Content-Type": "application/json",
                "x-api-key": API_KEY
            }
        }
        log(request)
        // Make the HTTP POST request to API Gateway
        let response = curl("POST",apiUrl,
            request
        );

        // Log the response (you might want to handle it differently)
        log("API Gateway response: ");
        log(response)
    } catch (e) {
        // Log any errors
        log("Error calling API Gateway: ");
        log(e)
    }
    
}