// Vercel serverless function - Proxy all /api/* requests to backend
// This handles HTTPS→HTTP conversion which browsers block

export default async function handler(req, res) {
    const BACKEND_URL = 'http://134.199.196.31:8000';
    
    // Get the full path after /api/
    const path = req.url;
    
    // Build full backend URL
    const backendUrl = `${BACKEND_URL}${path}`;
    
    try {
        // Forward the request to backend
        const response = await fetch(backendUrl, {
            method: req.method,
            headers: {
                'Content-Type': 'application/json',
                ...req.headers
            },
            body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined
        });
        
        // Get response data
        const data = await response.json();
        
        // Forward backend response to client
        res.status(response.status).json(data);
        
    } catch (error) {
        console.error('Proxy error:', error);
        res.status(500).json({ 
            success: false, 
            error: 'Backend connection failed',
            detail: error.message 
        });
    }
}

