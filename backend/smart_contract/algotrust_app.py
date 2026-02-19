from beaker import *
from pyteal import *

class AlgoTrustState:
    # --- Governance / Voting Global State ---
    proposal_title = GlobalStateValue(
        stack_type=TealType.bytes,
        descr="The title of the active campus proposal",
        default=Bytes("")
    )
    votes_yes = GlobalStateValue(
        stack_type=TealType.uint64,
        descr="Total tally of 'Yes' votes",
        default=Int(0)
    )
    votes_no = GlobalStateValue(
        stack_type=TealType.uint64,
        descr="Total tally of 'No' votes",
        default=Int(0)
    )
    voting_active = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Boolean: 1 if students can currently cast votes"
    )

    # --- Governance / Voting Local State ---
    voted_already = LocalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="1 if this specific student has already cast their vote"
    )

    # --- Crowdfunding Global State ---
    campaign_goal = GlobalStateValue(
        stack_type=TealType.uint64,
        descr="Target fundraising amount in microAlgos",
        default=Int(0)
    )
    total_raised = GlobalStateValue(
        stack_type=TealType.uint64,
        descr="Total microAlgos contributed so far",
        default=Int(0)
    )
    campaign_active = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Boolean: 1 if the campaign is open for contributions"
    )

app = Application("AlgoTrust", state=AlgoTrustState())

@app.create(bare=True)
def create():
    """Initializes the application global state."""
    return app.initialize_global_state()

@app.opt_in(bare=True)
def opt_in():
    """Initializes local state for the sender. Required for voting."""
    return app.initialize_local_state()

# --- GOVERNANCE METHODS ---

@app.external(authorize=Authorize.only_creator())
def start_proposal(title: abi.String):
    """
    Creator-only: Resets the voting tally and starts a new proposal.
    """
    return Seq(
        app.state.proposal_title.set(title.get()),
        app.state.votes_yes.set(Int(0)),
        app.state.votes_no.set(Int(0)),
        app.state.voting_active.set(Int(1))
    )

@app.external
def cast_vote(choice: abi.Uint64):
    """
    Public: Cast a vote (1 = Yes, 0 = No). 
    Requires student to be opted-in. Prevents double voting.
    """
    return Seq(
        Assert(app.state.voting_active.get() == Int(1), comment="Voting is currently closed"),
        Assert(app.state.voted_already.get() == Int(0), comment="Sender has already voted"),
        If(choice.get() == Int(1))
        .Then(app.state.votes_yes.increment())
        .Else(app.state.votes_no.increment()),
        app.state.voted_already.set(Int(1))
    )

@app.external(authorize=Authorize.only_creator())
def close_proposal():
    """Creator-only: Stops the voting process."""
    return app.state.voting_active.set(Int(0))

# --- CROWDFUNDING METHODS ---

@app.external(authorize=Authorize.only_creator())
def start_campaign(goal: abi.Uint64):
    """
    Creator-only: Starts a crowdfunding campaign with a target goal.
    """
    return Seq(
        app.state.campaign_goal.set(goal.get()),
        app.state.total_raised.set(Int(0)),
        app.state.campaign_active.set(Int(1))
    )

@app.external
def contribute(payment: abi.PaymentTransaction):
    """
    Public: Accepts a payment transaction toward the campaign.
    Must be grouped with a payment of > 0 ALGO to the App Account.
    """
    return Seq(
        Assert(app.state.campaign_active.get() == Int(1), comment="Campaign is inactive"),
        Assert(payment.get().receiver() == Global.current_application_address(), comment="Payment must go to app"),
        Assert(payment.get().amount() > Int(0), comment="Amount must be greater than 0"),
        app.state.total_raised.set(app.state.total_raised.get() + payment.get().amount())
    )

@app.external(authorize=Authorize.only_creator())
def withdraw_funds():
    """
    Creator-only: Withdraws funds to the creator's wallet if the goal is met.
    Keeps the minimum balance required to maintain the app.
    """
    return Seq(
        Assert(app.state.total_raised.get() >= app.state.campaign_goal.get(), comment="Goal not yet reached"),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: Global.creator_address(),
            # Calculation ensures we don't violate minimum balance requirements
            TxnField.amount: Balance(Global.current_application_address()) - Global.min_balance(),
            TxnField.fee: Int(0) # App account pays fee; must be funded or fee-pooled
        }),
        InnerTxnBuilder.Submit(),
        app.state.campaign_active.set(Int(0))
    )

@app.delete(authorize=Authorize.only_creator())
def delete():
    """Creator-only: Deletes the application."""
    return Approve()