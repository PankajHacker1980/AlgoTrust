from beaker import *
from pyteal import *

class AlgoTrustState:
    # --- Governance / Voting State ---
    proposal_title = GlobalStateValue(
        stack_type=TealType.bytes,
        descr="The title of the current campus proposal",
        default=Bytes("")
    )
    votes_yes = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Total tally of 'Yes' votes"
    )
    votes_no = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Total tally of 'No' votes"
    )
    voting_active = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="1 if voting is open"
    )
    campus_token_id = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="ASA ID representing Student ID. 0 means gated voting is disabled."
    )

    # --- Crowdfunding State ---
    campaign_goal = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Target amount in microAlgos"
    )
    total_raised = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0)
    )
    campaign_active = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0)
    )

    # --- Local State (User Specific) ---
    voted_already = LocalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Flag to prevent double voting"
    )
    contribution_balance = LocalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Tracks user contribution for potential refunds"
    )

app = Application("AlgoTrust", state=AlgoTrustState())

@app.create(bare=True)
def create():
    return app.initialize_global_state()

@app.opt_in(bare=True)
def opt_in():
    return app.initialize_local_state()

# --- ADMINISTRATIVE METHODS ---

@app.external(authorize=Authorize.only_creator())
def setup_campus_token(token: abi.Asset):
    """Sets the ASA ID that students must hold to be eligible to vote."""
    return app.state.campus_token_id.set(token.asset_id())

# --- GOVERNANCE METHODS ---

@app.external(authorize=Authorize.only_creator())
def start_proposal(title: abi.String):
    return Seq(
        app.state.proposal_title.set(title.get()),
        app.state.votes_yes.set(Int(0)),
        app.state.votes_no.set(Int(0)),
        app.state.voting_active.set(Int(1))
    )

@app.external
def cast_vote(choice: abi.Uint64):
    """
    Innovative Voting: Checks if the user holds the Campus ASA (Student ID Token) 
    before allowing a vote to be recorded.
    """
    # 1. Check if voting is active
    # 2. Check if user already voted (Local State)
    # 3. If a Campus Token is set, ensure sender has a balance >= 1
    get_token_bal = AssetHolding.balance(Txn.sender(), app.state.campus_token_id.get())
    
    return Seq(
        Assert(app.state.voting_active.get() == Int(1)),
        Assert(app.state.voted_already.get() == Int(0)),
        If(app.state.campus_token_id.get() != Int(0)).Then(
            Seq(
                get_token_bal,
                Assert(get_token_bal.hasValue()),
                Assert(get_token_bal.value() >= Int(1))
            )
        ),
        If(choice.get() == Int(1))
        .Then(app.state.votes_yes.increment())
        .Else(app.state.votes_no.increment()),
        app.state.voted_already.set(Int(1))
    )

@app.external(authorize=Authorize.only_creator())
def close_voting():
    return app.state.voting_active.set(Int(0))

# --- CROWDFUNDING METHODS ---

@app.external(authorize=Authorize.only_creator())
def start_campaign(goal: abi.Uint64):
    return Seq(
        app.state.campaign_goal.set(goal.get()),
        app.state.total_raised.set(Int(0)),
        app.state.campaign_active.set(Int(1))
    )

@app.external
def contribute(payment: abi.PaymentTransaction):
    """
    Contribute microAlgos. Tracks amount in local state to allow for 
    decentralized refunds if the goal is not met.
    """
    return Seq(
        Assert(app.state.campaign_active.get() == Int(1)),
        Assert(payment.get().receiver() == Global.current_application_address()),
        Assert(payment.get().amount() >= Int(100_000)),
        app.state.total_raised.set(app.state.total_raised.get() + payment.get().amount()),
        app.state.contribution_balance.set(
            app.state.contribution_balance.get() + payment.get().amount()
        )
    )

@app.external
def claim_refund():
    """
    Innovative Refund: If a campaign is closed and the goal was NOT reached,
    students can pull back their specific contribution.
    """
    return Seq(
        Assert(app.state.campaign_active.get() == Int(0)),
        Assert(app.state.total_raised.get() < app.state.campaign_goal.get()),
        Assert(app.state.contribution_balance.get() > Int(0)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: Txn.sender(),
            TxnField.amount: app.state.contribution_balance.get(),
            TxnField.fee: Int(1000)
        }),
        InnerTxnBuilder.Submit(),
        app.state.contribution_balance.set(Int(0))
    )

@app.external(authorize=Authorize.only_creator())
def withdraw_funds():
    """Withdraws funds to creator only if goal met."""
    return Seq(
        Assert(app.state.total_raised.get() >= app.state.campaign_goal.get()),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: Global.creator_address(),
            TxnField.amount: Balance(Global.current_application_address()) - Global.min_balance(),
            TxnField.fee: Int(0)
        }),
        InnerTxnBuilder.Submit(),
        app.state.campaign_active.set(Int(0))
    )

@app.delete(authorize=Authorize.only_creator())
def delete():
    return Approve()