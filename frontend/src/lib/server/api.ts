export function getApiBaseUrl(): string {
	return process.env.BACKEND_API_URL || 'http://127.0.0.1:8000';
}
