import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { chromium } from 'playwright';

const projectRoot = path.resolve('C:/Users/Sadjad Rgz/Documents/Majlesyar2');
const manifestPath = path.join(projectRoot, 'artifacts', 'pagespeed-reupload', 'manifest.json');
const screenshotDir = path.join(projectRoot, 'artifacts', 'pagespeed-reupload', 'screenshots');
const baseUrl = 'https://majlesyar.com';
const adminBase = `${baseUrl}/majmanage`;
const username = process.env.MAJLESYAR_ADMIN_USER || 'admin';
const password = process.env.MAJLESYAR_ADMIN_PASSWORD || 'admin';

async function readManifest() {
  const raw = await fs.readFile(manifestPath, 'utf8');
  return JSON.parse(raw);
}

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function login(page) {
  await page.goto(`${adminBase}/login/?next=/majmanage/`, { waitUntil: 'domcontentloaded' });
  await page.locator('input[name="username"]').fill(username);
  await page.locator('input[name="password"]').fill(password);
  await Promise.all([
    page.waitForURL(/\/majmanage\/$/),
    page.locator('button[type="submit"], input[type="submit"]').click(),
  ]);
}

async function verifyProductApi(item) {
  const response = await fetch(`${baseUrl}/api/v1/products/`, {
    headers: { accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`API check failed for ${item.slug}: ${response.status}`);
  }

  const products = await response.json();
  const current = products.find((entry) => entry.id === item.id || entry.url_slug === item.slug);
  if (!current) {
    throw new Error(`Could not find ${item.slug} in API response`);
  }

  if (current.image_name !== item.image_name) {
    throw new Error(`image_name changed for ${item.slug}: ${current.image_name}`);
  }
  if (current.image_alt !== item.image_alt) {
    throw new Error(`image_alt changed for ${item.slug}: ${current.image_alt}`);
  }
  if (!String(current.image || '').toLowerCase().endsWith('.webp')) {
    throw new Error(`image URL for ${item.slug} is not webp: ${current.image}`);
  }

  const imageResponse = await fetch(current.image, { redirect: 'follow' });
  const contentType = imageResponse.headers.get('content-type') || '';
  if (!imageResponse.ok) {
    throw new Error(`image URL failed for ${item.slug}: ${imageResponse.status}`);
  }
  if (!contentType.toLowerCase().includes('image/webp')) {
    throw new Error(`unexpected content type for ${item.slug}: ${contentType}`);
  }

  return {
    image: current.image,
    contentType,
  };
}

async function uploadProduct(page, item) {
  const changeUrl = `${adminBase}/catalog/product/${item.id}/change/`;
  const uploadPath = path.join(projectRoot, item.upload_ready);

  await page.goto(changeUrl, { waitUntil: 'domcontentloaded' });
  await page.locator('#id_name').waitFor();

  const [currentName, currentImageName, currentAlt] = await Promise.all([
    page.locator('#id_name').inputValue(),
    page.locator('#id_image_name').inputValue(),
    page.locator('#id_image_alt').inputValue(),
  ]);

  if (currentName !== item.name) {
    throw new Error(`Unexpected name on admin form for ${item.slug}: ${currentName}`);
  }
  if (currentImageName !== item.image_name) {
    throw new Error(`Unexpected image_name on admin form for ${item.slug}: ${currentImageName}`);
  }
  if (currentAlt !== item.image_alt) {
    throw new Error(`Unexpected image_alt on admin form for ${item.slug}: ${currentAlt}`);
  }

  await page.locator('#id_image').setInputFiles(uploadPath);

  await Promise.all([
    page.waitForLoadState('networkidle'),
    page.locator('[name="_save"]').click(),
  ]);

  const successMessage = page.locator('.messagelist .success, ul.messagelist li.success');
  await successMessage.waitFor();
}

async function screenshotPublicProduct(context, item) {
  const page = await context.newPage();
  await page.goto(`${baseUrl}/product/${item.slug}`, { waitUntil: 'networkidle' });
  await page.screenshot({
    path: path.join(screenshotDir, `${item.slug}.png`),
    fullPage: true,
  });
  await page.close();
}

async function main() {
  const manifest = await readManifest();
  await ensureDir(screenshotDir);

  const browser = await chromium.launch({
    channel: 'chrome',
    headless: true,
  });

  try {
    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();
    await login(adminPage);

    for (const item of manifest) {
      console.log(`Uploading ${item.slug} using ${item.upload_filename}`);
      await uploadProduct(adminPage, item);
      const verification = await verifyProductApi(item);
      console.log(`Verified ${item.slug}: ${verification.image} (${verification.contentType})`);
    }

    const publicContext = await browser.newContext();
    for (const item of manifest) {
      await screenshotPublicProduct(publicContext, item);
    }
    await publicContext.close();
    await adminContext.close();
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
