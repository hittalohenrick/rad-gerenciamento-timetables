const { expect } = require('@playwright/test');

async function clickSubmit(page, labelOrRegex) {
  await page.getByRole('button', { name: labelOrRegex }).click();
}

async function login(page, username, password) {
  await page.goto('/login');
  await page.fill('input[name="username"]', username);
  await page.fill('input[name="password"]', password);
  await clickSubmit(page, /entrar/i);
}

async function selectOptionByPartialText(page, selector, partialText) {
  const value = await page.$eval(
    selector,
    (select, text) => {
      const option = Array.from(select.options).find((item) =>
        (item.textContent || '').toLowerCase().includes(String(text).toLowerCase())
      );
      if (!option) {
        throw new Error(`Opcao nao encontrada em ${select.name || select.id}: ${text}`);
      }
      return option.value;
    },
    partialText
  );

  await page.selectOption(selector, value);
}

async function expectFlash(page, textOrRegex) {
  await expect(page.locator('.alert')).toContainText(textOrRegex);
}

module.exports = {
  clickSubmit,
  login,
  selectOptionByPartialText,
  expectFlash,
};
