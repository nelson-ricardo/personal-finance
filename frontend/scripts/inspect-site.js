import fs from 'node:fs';

async function run() {
	const newTabRes = await fetch('http://127.0.0.1:9222/json/new?http://localhost:5173/envelopes', {
		method: 'PUT'
	});
	const target = await newTabRes.json();
	const ws = new WebSocket(target.webSocketDebuggerUrl);
	let msgId = 1;
	const pending = new Map();
	function send(method, params = {}) {
		return new Promise((resolve, reject) => {
			const id = msgId++;
			pending.set(id, { resolve, reject });
			ws.send(JSON.stringify({ id, method, params }));
		});
	}
	ws.onmessage = (event) => {
		const msg = JSON.parse(event.data);
		if (msg.id && pending.has(msg.id)) {
			const { resolve, reject } = pending.get(msg.id);
			pending.delete(msg.id);
			if (msg.error) reject(new Error(msg.error.message));
			else resolve(msg.result);
		}
	};
	await new Promise((resolve) => (ws.onopen = resolve));
	await send('Page.enable');
	await send('Runtime.enable');

	await send('Emulation.setDeviceMetricsOverride', {
		width: 1440,
		height: 900,
		deviceScaleFactor: 1,
		mobile: false
	});
	await new Promise((r) => setTimeout(r, 1200));

	// Open Transfer Modal
	await send('Runtime.evaluate', {
		expression: `(() => {
			const btns = Array.from(document.querySelectorAll('button'));
			const btn = btns.find(b => b.textContent.includes('Transfer'));
			if (btn) btn.click();
		})()`
	});
	await new Promise((r) => setTimeout(r, 600));

	const transferScreenshot = await send('Page.captureScreenshot', { format: 'png' });
	fs.writeFileSync('screenshot-envelopes-transfer-modal.png', Buffer.from(transferScreenshot.data, 'base64'));

	await fetch(`http://127.0.0.1:9222/json/close/${target.id}`);
	ws.close();
}

run().catch(console.error);
