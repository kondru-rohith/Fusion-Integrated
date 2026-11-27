import {
  expect, openModuleNav, sidebar, signedInAs, test,
} from "../support/test";

test.describe("spacs: catalogue (UC-SPACS-001)", () => {
  test.use(signedInAs("student"));

  test("a student can navigate to SPACS and browse scholarship schemes", async ({ page }) => {
    await page.goto("/");
    await openModuleNav(page, "Awards & Scholarships");
    await sidebar(page).getByRole("link", { name: "Opportunities" }).click();

    await expect(page.getByRole("heading", { name: /Scholarship & Award Opportunities/i })).toBeVisible();
    await expect(page.getByText(/Explore active institutional scholarships/i)).toBeVisible();
  });
});
