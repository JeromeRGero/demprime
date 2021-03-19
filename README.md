# Democracy Prime

This is a discord bot used to automate a community servers voting rules when votes are submitted to the `#votes` channel.

Thumbsup for aye.
Thumbsdowm for nay.
Questionmark for abstain.

## TLDR;
This bot is being made as a way to fairly make decisions within a group of friends, in which there is no one at the head of the round table (except for maybe me :p).

## How does voting work?
Voters have the ability to respond with: 
`Thumbsup` for yes `Thumbsdown` for no, or :Questionmark: for abstain. 
Please note that abstained votes-while they are neither yes or no, are still counted as votes which counts towards the overall population's participation.

## Nitty Gritty Numbers
40% of the overall population of the server is required to vote with a`Thumbsup` in order for a vote to pass, however, this can technically still be blocked. 
> - For instance, if 40% of the server did not vote, then the vote will be default NOT pass after the expiration date of the vote has been met, typically 3 days. This is why picking and choosing who is involved in the server from those who start it, and making sure that they will be an active member is beneficial for *everyone* involved. 
> - What happens if exactly 40 or more of the server votes with a `Thumbsdown` (keeping in mind that they would have to be voting strictly-`Thumbsdown` and not `Questionmark`to abstain)?  If the % of `Thumbsdown` is over 50% of the overall server population, then the vote automatically fails to pass. If the number of `Thumbsdown` are equal to or greater than the number of `Thumbsup` but the number of `Thumbsdown` is not over 50%, then the vote will be elevated up to the server’s administrators, of which is made up of founding and non-founding members of the server. That vote is currently not planned to be automated by the discord bot (Democracy Prime) but could be in the future.
