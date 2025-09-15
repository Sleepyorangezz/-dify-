// Vercel Edge Function: /api/proxy.js

export const config = {
  runtime: 'edge',
};

export default async function handler(request) {
  // 只接受 POST 请求
  if (request.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 });
  }

  try {
    const body = await request.json();
    const urlToSummarize = body.url;

    if (!urlToSummarize) {
      return new Response(JSON.stringify({ error: 'URL is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // 从环境变量中安全地获取 Dify API Key
    const difyApiKey = process.env.DIFY_API_KEY;
    if (!difyApiKey) {
        return new Response(JSON.stringify({ error: 'Server configuration error: API key not set' }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' },
        });
    }

    // 在后端调用 Dify API
    const difyResponse = await fetch('https://api.dify.ai/v1/workflows/run', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${difyApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        inputs: {
          query: urlToSummarize,
        },
        response_mode: 'blocking',
        user: 'secure-vercel-user', // 可以使用一个固定的、安全的 user id
      }),
    });

    const difyData = await difyResponse.json();

    // 将 Dify 的响应返回给前端
    return new Response(JSON.stringify(difyData), {
      status: difyResponse.status,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
