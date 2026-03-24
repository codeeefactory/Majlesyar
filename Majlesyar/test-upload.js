import fetch from 'node-fetch';
import FormData from 'form-data';
import fs from 'fs';

// Replace with your backend URL
const API_BASE_URL = 'http://localhost:8000';

// Admin credentials (set these)
const ADMIN_USERNAME = 'your_admin_username';
const ADMIN_PASSWORD = 'your_admin_password';

// Path to an example image file (e.g., a small PNG or JPG)
const IMAGE_PATH = './example-image.png'; // Make sure this file exists

async function login() {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: ADMIN_USERNAME,
      password: ADMIN_PASSWORD,
    }),
  });

  if (!response.ok) {
    throw new Error('Login failed');
  }

  const data = await response.json();
  return data.access; // JWT access token
}

async function uploadProductImage(accessToken) {
  const formData = new FormData();
  formData.append('name', 'Test Product with Image');
  formData.append('url_slug', 'test-product-image');
  formData.append('description', 'A test product to upload an image.');
  formData.append('price', '100000'); // Example price in IRR
  formData.append('category_ids', '[]'); // Empty array or actual IDs
  formData.append('event_types', '["conference"]');
  formData.append('contents', '["Item 1", "Item 2"]');
  formData.append('image_alt', 'Test image alt text');
  formData.append('image_name', 'test-image');
  formData.append('featured', 'false');
  formData.append('available', 'true');

  // Append the image file
  formData.append('image_file', fs.createReadStream(IMAGE_PATH));

  const response = await fetch(`${API_BASE_URL}/api/v1/admin/products/`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Upload failed: ${response.status} ${error}`);
  }

  const result = await response.json();
  console.log('Product created successfully:', result);
}

async function main() {
  try {
    console.log('Logging in...');
    const accessToken = await login();

    console.log('Uploading product with image...');
    await uploadProductImage(accessToken);

    console.log('Done!');
  } catch (error) {
    console.error('Error:', error.message);
  }
}

main();