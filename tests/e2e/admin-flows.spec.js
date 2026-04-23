const { test, expect } = require('@playwright/test');
const { clickSubmit, expectFlash, login, selectOptionByPartialText } = require('./helpers/ui-helpers');

function uniqueSuffix() {
  return String(Date.now()).slice(-6);
}

test.describe('Fluxos E2E - Admin', () => {
  test('admin acessa dashboard e telas de gestao', async ({ page }) => {
    await login(page, 'admin', 'Admin1234');

    await expect(page.getByRole('heading', { name: 'Dashboard Administrativo' })).toBeVisible();

    await page.goto('/salas');
    await expect(page.getByRole('heading', { name: 'Salas' })).toBeVisible();

    await page.goto('/disciplinas');
    await expect(page.getByRole('heading', { name: 'Disciplinas' })).toBeVisible();

    await page.goto('/professores');
    await expect(page.getByRole('heading', { name: 'Professores' })).toBeVisible();

    await page.goto('/alunos');
    await expect(page.getByRole('heading', { name: 'Alunos' })).toBeVisible();

    await page.goto('/matriculas');
    await expect(page.getByRole('heading', { name: /Aloca.+de Alunos/i })).toBeVisible();
  });

  test('admin cadastra entidades e aloca aluno em turma', async ({ page }) => {
    const suffix = uniqueSuffix();

    const salaNome = `Sala E2E ${suffix}`;
    const disciplinaNome = `Disciplina E2E ${suffix}`;
    const professorLogin = `prof.e2e.${suffix}`;
    const alunoNome = `Aluno E2E ${suffix}`;
    const alunoMatricula = `20261BCC${suffix}`;

    await login(page, 'admin', 'Admin1234');

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
    await page.fill('input[name="password"]', 'ProfE2e123');
    await page.fill('input[name="password2"]', 'ProfE2e123');
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
  });
});
