# Integration of IPV6 work into unified project with the HA work
## Goal
Your goal is to evaluate the project in https://github.com/ttickell/opnsense-ipv6.git - already a submodule here under opnsense-ipv6 - and integrate it into the current opnsense-ha project in a manner compliant with opnsense standards and best practices while retaining the functionality the IPV6 work creates - specifically the nuances of how to gather delegations for AT&T and Comcast, the use of a specific ULA on our networks, and the mapping process to ensure the ULAs are mapped to prefixes we are delegated and that the mappings are in place for both providers so IPv6 functionality is seamless in the event of a failover. 

Additionally, you will need to improve current state to add the mapping process so that it is triggered when we receive new delegations. 

## Background Information
The explanation of the reasoning for this manner of handling IPv6 is in the README.MD file of that repository.  Likewise, the repository documents the ULA in use and it's subdivision in GeneralNotes.md.  

Opnsense-core has been added as a submodule here, too.  The OPNSense codebase should be consulted to confirm or update each choice you make regarding how to bring this into standards / best practices.  

The OPNsense documentation is at https://docs.opnsense.org/.  You will also consult it to determine best practice and standard.

Opnsense forums are at https://forum.opnsense.org.  You will consult these to reveal prior issues / solutions from the community as required to help guide your work or any issues we encounter while testing.

Our TODO.md has prior work / analysis you did regarding what was required / gaps to be closed.  You may use that as a staring point, but we did not return to first principals / references to validate your assumptions in that pass.

Finally, HOW_TO_DEBUG.md has information about prior mistakes made due to making assumptions.  You will refer to this and your plan to do better going forward to ensure there are not assumptions made which are not validated with a definitive source.

## Your Tasks
* Consume all available background information
* Repeat your original gap analysis, but with the definitive source information in mind
* Build an plan to integrate the IPv6 work with the HA work, including setup steps.

Take no action until the plan is reviewed and approved buy me.
