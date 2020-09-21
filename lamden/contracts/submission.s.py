# Test sync

@__export('submission')
def submit_contract(name: str, code: str, owner: Any=None, constructor_args: dict={}):
    assert not name.isdigit() and all(c.isalnum() or c == '_' for c in name), 'Invalid contract name!!!'
    __Contract().submit(name=name, code=code, owner=owner, constructor_args=constructor_args, developer=ctx.caller)


@__export('submission')
def change_developer(contract: str, new_developer: str):
    d = __Contract()._driver.get_var(contract=contract, variable='__developer__')
    assert ctx.caller == d, 'Sender is not current developer!'

    __Contract()._driver.set_var(contract=contract,
                                 variable='__developer__',
                                 value=new_developer)
