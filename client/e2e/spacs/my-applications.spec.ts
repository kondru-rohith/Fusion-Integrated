import {
  expect, openModuleNav, sidebar, signedInAs, test,
} from "../support/test";

test.describe("spacs: my applications (UC-SPACS-002, 004)", () => {
  test.use(signedInAs("student"));

  test("a student can view their submitted applications dashboard", async ({ page }) => {
    await page.goto("/");
    await openModuleNav(page, "Awards & Scholarships");
    await sidebar(page).getByRole("link", { name: "My Applications" }).click();

    await expect(page.getByRole("heading", { name: /My Scholarship Applications/i })).toBeVisible();
    await expect(page.getByText(/Track submitted applications, verification findings/i)).toBeVisible();
  });
});
