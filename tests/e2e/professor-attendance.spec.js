const { test, expect } = require('@playwright/test');
const { expectFlash, login } = require('./helpers/ui-helpers');

test.describe('Fluxos E2E - Professor e Chamada', () => {
  test('professor nao acessa dashboard admin', async ({ page }) => {
    await login(page, 'prof.demo', 'ProfDemo123');
    await expect(page.getByRole('heading', { name: 'Minhas Turmas' })).toBeVisible();

    await page.goto('/admin');
    await expectFlash(page, 'Acesso restrito ao administrador.');
    await expect(page.getByRole('heading', { name: 'Minhas Turmas' })).toBeVisible();
  });

  test('professor usa busca e marca chamada com validacoes', async ({ page }) => {
    await login(page, 'prof.demo', 'ProfDemo123');

    await page.getByRole('link', { name: 'Fazer Chamada' }).first().click();
    await expect(page.getByRole('heading', { name: 'Chamada da Turma' })).toBeVisible();

    await expect(page.locator('#summary-total')).toHaveText('3');
    await expect(page.getByRole('cell', { name: '01/04/2026' })).toBeVisible();

    await page.fill('#attendance-search', 'Dois');
    await page.click('#mark-visible-present');
    await expect(page.locator('#summary-present')).toHaveText('1');

    await page.click('#clear-visible-present');
    await expect(page.locator('#summary-present')).toHaveText('0');

    await page.fill('#attendance-search', '');
    await page.click('#mark-visible-present');
    await expect(page.locator('#summary-present')).toHaveText('3');

    await page.fill('input[name="chamada_data"]', '2026-04-10');
    await page.getByRole('button', { name: 'Salvar Chamada' }).click();
    await expectFlash(page, /deve corresponder ao dia da turma/i);

    await page.fill('input[name="chamada_data"]', '2026-04-08');
    await page.click('#clear-visible-present');
    await page.click('#mark-visible-present');
    await page.getByRole('button', { name: 'Salvar Chamada' }).click();

    await expectFlash(page, 'Chamada salva com sucesso.');
    await expect(page.getByRole('cell', { name: '08/04/2026' })).toBeVisible();
    await expect(page.locator('#summary-present')).toHaveText('3');
  });
});
