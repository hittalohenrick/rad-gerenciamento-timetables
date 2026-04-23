const { test, expect } = require('@playwright/test');
const { clickSubmit, expectFlash, login, selectOptionByPartialText } = require('./helpers/ui-helpers');

function uniqueSuffix() {
  return String(Date.now()).slice(-6);
}

test.describe('Fluxo E2E Completo', () => {
  test('admin e professor percorrem funcionalidades principais de ponta a ponta', async ({ page }) => {
    const suffix = uniqueSuffix();

    const salaNome = `Sala Full ${suffix}`;
    const disciplinaNome = `Disciplina Full ${suffix}`;
    const professorLogin = `prof.full.${suffix}`;
    const alunoNome = `Aluno Full ${suffix}`;
    const alunoMatricula = `20261BCCF${suffix}`;

    // Admin: valida navegacao principal e cria entidades.
    await login(page, 'admin', 'Admin1234');
    await expect(page.getByRole('heading', { name: 'Dashboard Administrativo' })).toBeVisible();

    await page.goto('/sala/new');
    await page.fill('input[name="nome"]', salaNome);
    await page.fill('input[name="capacidade"]', '35');
    await clickSubmit(page, /salvar/i);
    await expectFlash(page, 'Sala criada com sucesso.');

    await page.goto('/disciplina/new');
    await page.fill('input[name="nome"]', disciplinaNome);
    await clickSubmit(page, /salvar/i);
    await expectFlash(page, 'Disciplina criada com sucesso.');

    await page.goto('/professor/new');
    await page.fill('input[name="username"]', professorLogin);
    await page.fill('input[name="password"]', 'ProfFull123');
    await page.fill('input[name="password2"]', 'ProfFull123');
    await clickSubmit(page, /salvar/i);
    await expectFlash(page, 'Professor registrado com sucesso.');

    await page.goto('/aluno/new');
    await page.fill('input[name="nome"]', alunoNome);
    await page.fill('input[name="matricula"]', alunoMatricula);
    await clickSubmit(page, /salvar/i);
    await expectFlash(page, 'Aluno cadastrado com sucesso.');

    await page.goto('/timetable/new');
    await page.selectOption('select[name="dia"]', 'Quarta');
    await page.fill('input[name="hora_inicio"]', '14:00');
    await page.fill('input[name="hora_fim"]', '15:40');
    await selectOptionByPartialText(page, 'select[name="sala_id"]', salaNome);
    await selectOptionByPartialText(page, 'select[name="professor_id"]', professorLogin);
    await selectOptionByPartialText(page, 'select[name="disciplina_id"]', disciplinaNome);
    await clickSubmit(page, /alocar/i);
    await expectFlash(page, 'Alocacao criada com sucesso.');

    await page.goto('/matricula/new');
    await selectOptionByPartialText(page, 'select[name="aluno_id"]', alunoMatricula);
    await selectOptionByPartialText(page, 'select[name="timetable_id"]', professorLogin);
    await clickSubmit(page, /alocar/i);
    await expectFlash(page, 'Aluno alocado com sucesso.');

    await page.goto('/matriculas');
    await expect(page.getByText(alunoMatricula)).toBeVisible();
    await expect(page.getByText(professorLogin)).toBeVisible();

    // Admin encerra sessao.
    await page.goto('/logout');
    await expect(page).toHaveURL(/\/login/);

    // Professor: valida dashboard e fluxo de chamada.
    await login(page, professorLogin, 'ProfFull123');
    await expect(page.getByRole('heading', { name: 'Minhas Turmas' })).toBeVisible();

    await page.getByRole('link', { name: 'Fazer Chamada' }).first().click();
    await expect(page.getByRole('heading', { name: 'Chamada da Turma' })).toBeVisible();

    await page.fill('#attendance-search', alunoNome.split(' ')[0]);
    await page.click('#mark-visible-present');
    await page.click('#clear-visible-present');
    await page.fill('#attendance-search', '');
    await page.click('#mark-visible-present');

    // Data invalida (dia errado) para validar regra.
    await page.fill('input[name="chamada_data"]', '10/04/2026');
    await page.getByRole('button', { name: 'Salvar Chamada' }).click();
    await expectFlash(page, /deve corresponder ao dia da turma/i);

    // Data valida para salvar chamada com sucesso.
    await page.fill('input[name="chamada_data"]', '08/04/2026');
    await page.click('#mark-visible-present');
    await page.getByRole('button', { name: 'Salvar Chamada' }).click();
    await expectFlash(page, 'Chamada salva com sucesso.');
  });
});
