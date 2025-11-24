// Proxy for /api/search/{id}
export default async function handler(req, res) {
    // Enable CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    const BACKEND_URL = 'http://134.199.196.31:8000';
    const { id } = req.query;
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/search/${id}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        const data = await response.json();
        return res.status(response.status).json(data);
        
    } catch (error) {
        console.error('Proxy error:', error);
        return res.status(500).json({ 
            success: false, 
            error: 'Backend connection failed',
            detail: error.message
        });
    }
}
