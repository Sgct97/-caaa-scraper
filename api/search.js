// Proxy for /api/search
export default async function handler(req, res) {
    const BACKEND_URL = 'http://134.199.196.31:8000';
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(req.body),
        });
        
        const data = await response.json();
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

