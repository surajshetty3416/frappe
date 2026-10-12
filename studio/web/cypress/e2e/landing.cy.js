describe("Builder Dashboard", () => {
	before(() => {
		cy.login();
	});
	it("Open builder page", () => {
		cy.visit("studio/web");
	});
});
