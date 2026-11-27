import { expect, signedInAs, test } from "../support/test";

// Office pages that must not be accessible to students without elevated permissions
const OFFICE_PAGES = [
  "verification-queue",
  "decision-queue",
  "catalogue-admin",
  "awards",
  "audit",
];

test.describe("spacs: office route guards", () => {
  test.use(signedInAs("student"));

  for (const path of OFFICE_PAGES) {
    test(`a student who opens /spacs/${path} is denied access by role guard`, async ({ page }) => {
      await page.goto(`/spacs/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
