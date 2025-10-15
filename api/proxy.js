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
    // --- 修改: 从请求体中解构出 url 和 contentType ---
    const { url: urlToSummarize, contentType } = body;

    // --- 修改: 增加对 contentType 的校验 ---
    if (!urlToSummarize || !contentType) {
      return new Response(JSON.stringify({ error: 'URL and contentType are required' }), {
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
        // --- 核心修改: 将 contentType 添加到 inputs 对象中 ---
        inputs: {
          query: urlToSummarize,
          // 这里的键名 "CONTENT_TYPE" 必须与您在 Dify 工作流「开始」节点中定义的变量名完全一致！
          CONTENT_TYPE: contentType, 
        },
        response_mode: 'blocking',
        user: 'secure-vercel-user',
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
